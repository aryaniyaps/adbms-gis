import streamlit as st
import pymongo
import folium
from streamlit_folium import st_folium
import pandas as pd
from geopy.geocoders import Nominatim
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import numpy as np
from sklearn.cluster import DBSCAN
import json
from bson import ObjectId

# MongoDB connection
@st.cache_resource
def init_connection():
    return pymongo.MongoClient("mongodb://user:pass@localhost:27018/?directConnection=true")

@st.cache_data
def get_jobs():
    client = init_connection()
    db = client.job_portal
    jobs = list(db.jobs.find())
    for job in jobs:
        job['_id'] = str(job['_id'])
    return jobs

@st.cache_data
def get_tech_hubs():
    client = init_connection()
    db = client.job_portal
    return list(db.tech_hubs.find())

@st.cache_data
def get_salary_zones():
    client = init_connection()
    db = client.job_portal
    return list(db.salary_zones.find())

@st.cache_data
def get_market_data():
    client = init_connection()
    db = client.job_portal
    return list(db.market_analysis.find())

def spatial_query_jobs(center_lat, center_lng, radius_km):
    client = init_connection()
    db = client.job_portal
    
    query = {
        "coordinates": {
            "$geoWithin": {
                "$centerSphere": [[center_lng, center_lat], radius_km / 6371]
            }
        }
    }
    return list(db.jobs.find(query))

def cluster_jobs(jobs):
    if len(jobs) < 2:
        return jobs
    
    coords = np.array([[job['coordinates'][1], job['coordinates'][0]] for job in jobs])
    clustering = DBSCAN(eps=0.1, min_samples=2).fit(coords)
    
    for i, job in enumerate(jobs):
        job['cluster'] = int(clustering.labels_[i])
    
    return jobs

def add_job(job_data):
    client = init_connection()
    db = client.job_portal
    db.jobs.insert_one(job_data)

def geocode_location(location):
    geolocator = Nominatim(user_agent="job_portal")
    try:
        location_data = geolocator.geocode(location)
        return location_data.latitude, location_data.longitude
    except:
        return None, None

# Alert Management Functions
def create_alert(alert_data):
    """Create a new job alert"""
    client = init_connection()
    db = client.job_portal
    alert_data['created_at'] = datetime.now()
    alert_data['last_checked'] = datetime.now()
    alert_data['is_active'] = True
    return db.alerts.insert_one(alert_data)

def get_user_alerts(user_email):
    """Get all alerts for a user"""
    client = init_connection()
    db = client.job_portal
    alerts = list(db.alerts.find({"user_email": user_email, "is_active": True}))
    for alert in alerts:
        alert['_id'] = str(alert['_id'])
    return alerts

def delete_alert(alert_id):
    """Delete an alert"""
    client = init_connection()
    db = client.job_portal
    db.alerts.update_one({"_id": ObjectId(alert_id)}, {"$set": {"is_active": False}})

def check_geofence_alerts(alert):
    """Check if new jobs match geofence alert"""
    client = init_connection()
    db = client.job_portal
    
    # Find jobs posted since last check
    query = {
        "coordinates": {
            "$geoWithin": {
                "$centerSphere": [
                    [alert['center_lng'], alert['center_lat']], 
                    alert['radius_km'] / 6371
                ]
            }
        },
        "created_at": {"$gte": alert['last_checked']}
    }
    
    # Add category filter if specified
    if alert.get('category'):
        query['category'] = alert['category']
    
    # Add minimum salary filter if specified
    if alert.get('min_salary'):
        query['salary'] = {"$gte": alert['min_salary']}
    
    new_jobs = list(db.jobs.find(query))
    return new_jobs

def check_salary_increase_alerts(alert):
    """Check if salaries increased in target area"""
    client = init_connection()
    db = client.job_portal
    
    # Get recent jobs in the area
    recent_jobs = list(db.jobs.find({
        "coordinates": {
            "$geoWithin": {
                "$centerSphere": [
                    [alert['center_lng'], alert['center_lat']], 
                    alert['radius_km'] / 6371
                ]
            }
        },
        "created_at": {"$gte": datetime.now() - timedelta(days=7)}
    }))
    
    if not recent_jobs:
        return []
    
    # Calculate average salary
    avg_salary = np.mean([job['salary'] for job in recent_jobs])
    
    # Check if it's higher than alert threshold
    if avg_salary > alert.get('target_salary', 0):
        return [{
            'type': 'salary_increase',
            'message': f"Average salary increased to ${avg_salary:,.0f} in {alert.get('location_name', 'your area')}",
            'avg_salary': avg_salary,
            'job_count': len(recent_jobs)
        }]
    
    return []

def check_new_company_alerts(alert):
    """Check for new companies in the area"""
    client = init_connection()
    db = client.job_portal
    
    # Get companies that posted jobs since last check
    pipeline = [
        {
            "$match": {
                "coordinates": {
                    "$geoWithin": {
                        "$centerSphere": [
                            [alert['center_lng'], alert['center_lat']], 
                            alert['radius_km'] / 6371
                        ]
                    }
                },
                "created_at": {"$gte": alert['last_checked']}
            }
        },
        {
            "$group": {
                "_id": "$company",
                "first_job": {"$first": "$$ROOT"},
                "job_count": {"$sum": 1}
            }
        }
    ]
    
    new_companies = list(db.jobs.aggregate(pipeline))
    return new_companies

def save_alert_notification(user_email, alert_id, notification_data):
    """Save notification to database"""
    client = init_connection()
    db = client.job_portal
    
    notification = {
        "user_email": user_email,
        "alert_id": alert_id,
        "notification_type": notification_data.get('type', 'new_jobs'),
        "message": notification_data.get('message', ''),
        "data": notification_data,
        "created_at": datetime.now(),
        "is_read": False
    }
    
    db.notifications.insert_one(notification)

def get_user_notifications(user_email, limit=10):
    """Get recent notifications for user"""
    client = init_connection()
    db = client.job_portal
    
    notifications = list(
        db.notifications.find({"user_email": user_email})
        .sort("created_at", -1)
        .limit(limit)
    )
    
    for notif in notifications:
        notif['_id'] = str(notif['_id'])
    
    return notifications

def mark_notification_read(notification_id):
    """Mark notification as read"""
    client = init_connection()
    db = client.job_portal
    db.notifications.update_one(
        {"_id": ObjectId(notification_id)}, 
        {"$set": {"is_read": True}}
    )

st.set_page_config(page_title="Advanced GIS Job Portal", layout="wide")

st.title("🌍 Advanced GIS Job Portal")
st.markdown("*Sophisticated geospatial analysis for job market intelligence*")

# Sidebar
st.sidebar.header("🗺️ Navigation")
page = st.sidebar.selectbox("Choose Analysis", [
    "Interactive Job Map", 
    "Spatial Analytics", 
    "Salary Heatmap", 
    "Market Intelligence",
    "Job Alerts & Notifications",
    "Add Job"
])

if page == "Interactive Job Map":
    st.header("🎯 Interactive Job Map with Clustering")
    
    # Initialize session state for jobs
    if 'filtered_jobs_list' not in st.session_state:
        st.session_state.filtered_jobs_list = None
    if 'search_active' not in st.session_state:
        st.session_state.search_active = False
    
    tech_hubs = get_tech_hubs()
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.subheader("🔍 Spatial Filters")
        
        # Radius search
        search_enabled = st.checkbox("Enable Radius Search")
        if search_enabled:
            search_lat = st.number_input("Latitude", value=37.7749, format="%.4f")
            search_lng = st.number_input("Longitude", value=-122.4194, format="%.4f")
            radius = st.slider("Radius (km)", 1, 100, 25)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("Search Jobs"):
                    st.session_state.filtered_jobs_list = spatial_query_jobs(search_lat, search_lng, radius)
                    st.session_state.search_active = True
                    st.success(f"Found {len(st.session_state.filtered_jobs_list)} jobs within {radius}km")
            with col_btn2:
                if st.button("Reset Search"):
                    st.session_state.filtered_jobs_list = None
                    st.session_state.search_active = False
                    st.rerun()
    
    # Determine which jobs to display
    if st.session_state.search_active and st.session_state.filtered_jobs_list is not None:
        jobs = st.session_state.filtered_jobs_list
    else:
        jobs = get_jobs()
        
    with col2:
        # Clustering
        enable_clustering = st.checkbox("Enable Job Clustering", value=True)
        
        # Filters
        if jobs:
            categories = list(set([job['category'] for job in jobs]))
            selected_categories = st.multiselect("Categories", categories, default=categories)
            
            salary_range = st.slider("Salary Range", 
                                   min_value=min([job['salary'] for job in jobs]),
                                   max_value=max([job['salary'] for job in jobs]),
                                   value=(min([job['salary'] for job in jobs]), 
                                         max([job['salary'] for job in jobs])))
    
    with col1:
        if jobs:
            # Filter jobs
            filtered_jobs = [job for job in jobs 
                           if job['category'] in selected_categories 
                           and salary_range[0] <= job['salary'] <= salary_range[1]]
            
            if enable_clustering:
                filtered_jobs = cluster_jobs(filtered_jobs)
            
            # Create advanced map
            center_lat = np.mean([job['coordinates'][1] for job in filtered_jobs])
            center_lng = np.mean([job['coordinates'][0] for job in filtered_jobs])
            
            m = folium.Map(location=[center_lat, center_lng], zoom_start=6)
            
            # Add tech hub polygons
            for hub in tech_hubs:
                folium.GeoJson(
                    hub['geometry'],
                    style_function=lambda x: {
                        'fillColor': 'lightblue',
                        'color': 'blue',
                        'weight': 2,
                        'fillOpacity': 0.3
                    },
                    popup=f"Tech Hub: {hub['name']}<br>Avg Salary: ${hub['avg_salary']:,}"
                ).add_to(m)
            
            # Add clustered job markers
            cluster_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen']
            
            for job in filtered_jobs:
                color = cluster_colors[job.get('cluster', 0) % len(cluster_colors)] if enable_clustering else 'blue'
                
                popup_text = f"""
                <b>{job['title']}</b><br>
                Company: {job['company']}<br>
                Salary: ${job['salary']:,}<br>
                Type: {job['job_type']}<br>
                Location: {job['location']}<br>
                Remote: {'Yes' if job.get('remote_friendly') else 'No'}
                """
                
                folium.CircleMarker(
                    [job['coordinates'][1], job['coordinates'][0]],
                    radius=8,
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=job['title'],
                    color=color,
                    fillColor=color,
                    fillOpacity=0.7
                ).add_to(m)
            
            # Add search radius if enabled
            if search_enabled:
                folium.Circle(
                    [search_lat, search_lng],
                    radius=radius * 1000,
                    color='red',
                    fillColor='red',
                    fillOpacity=0.1
                ).add_to(m)
            
            st_folium(m, width=700, height=600)
            
            st.subheader(f"📊 Found {len(filtered_jobs)} Jobs")
            if filtered_jobs:
                df = pd.DataFrame(filtered_jobs)
                display_cols = ['title', 'company', 'location', 'salary', 'job_type', 'category']
                st.dataframe(df[display_cols], use_container_width=True)

elif page == "Spatial Analytics":
    st.header("📈 Advanced Spatial Analytics")
    
    jobs = get_jobs()
    
    if jobs:
        df = pd.DataFrame(jobs)
        
        # Spatial statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Jobs", len(jobs))
            st.metric("Unique Cities", df['location'].nunique())
        
        with col2:
            # Calculate job density by city
            city_counts = df['location'].value_counts()
            st.metric("Highest Density", f"{city_counts.index[0]} ({city_counts.iloc[0]})")
        
        with col3:
            # Geographic spread
            lats = [job['coordinates'][1] for job in jobs]
            lngs = [job['coordinates'][0] for job in jobs]
            spread = ((max(lats) - min(lats)) + (max(lngs) - min(lngs))) / 2
            st.metric("Geographic Spread", f"{spread:.2f}°")
        
        # Distance analysis
        st.subheader("🎯 Distance-Based Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Job density heatmap
            fig = go.Figure(data=go.Scattermapbox(
                lat=[job['coordinates'][1] for job in jobs],
                lon=[job['coordinates'][0] for job in jobs],
                mode='markers',
                marker=dict(
                    size=[job['salary']/5000 for job in jobs],
                    color=[job['salary'] for job in jobs],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Salary")
                ),
                text=[f"{job['title']}<br>${job['salary']:,}" for job in jobs],
                hovertemplate='%{text}<extra></extra>'
            ))
            
            fig.update_layout(
                mapbox=dict(
                    style="open-street-map",
                    center=dict(lat=39.8283, lon=-98.5795),
                    zoom=3
                ),
                height=400,
                title="Job Salary Distribution Map"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Nearest neighbor analysis
            st.subheader("🔍 Spatial Clustering Analysis")
            
            coords = np.array([[job['coordinates'][1], job['coordinates'][0]] for job in jobs])
            clustering = DBSCAN(eps=0.5, min_samples=3).fit(coords)
            
            cluster_counts = pd.Series(clustering.labels_).value_counts()
            cluster_counts = cluster_counts[cluster_counts.index != -1]  # Remove noise
            
            if len(cluster_counts) > 0:
                fig = px.bar(
                    x=cluster_counts.index,
                    y=cluster_counts.values,
                    title="Job Clusters",
                    labels={'x': 'Cluster ID', 'y': 'Jobs in Cluster'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No significant clusters found")

elif page == "Salary Heatmap":
    st.header("💰 Salary Heatmap Analysis")
    
    jobs = get_jobs()
    salary_zones = get_salary_zones()
    
    if jobs and salary_zones:
        # Create salary heatmap
        m = folium.Map(location=[39.8283, -98.5795], zoom_start=4)
        
        # Add salary zones as circles
        for zone in salary_zones:
            folium.Circle(
                [zone['center'][1], zone['center'][0]],
                radius=zone['radius_km'] * 1000,
                color='red' if zone['avg_salary'] > 150000 else 'orange' if zone['avg_salary'] > 100000 else 'green',
                fillColor='red' if zone['avg_salary'] > 150000 else 'orange' if zone['avg_salary'] > 100000 else 'green',
                fillOpacity=0.3,
                popup=f"City: {zone['city']}<br>Avg Salary: ${zone['avg_salary']:,}<br>Jobs: {zone['job_count']}"
            ).add_to(m)
        
        # Add job points
        for job in jobs:
            folium.CircleMarker(
                [job['coordinates'][1], job['coordinates'][0]],
                radius=5,
                color='blue',
                fillColor='lightblue',
                fillOpacity=0.8,
                popup=f"{job['title']}<br>${job['salary']:,}"
            ).add_to(m)
        
        st_folium(m, width=700, height=500)
        
        # Salary statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Salary Distribution by City")
            df = pd.DataFrame(jobs)
            city_salaries = df.groupby('location')['salary'].agg(['mean', 'count']).reset_index()
            city_salaries.columns = ['City', 'Avg Salary', 'Job Count']
            city_salaries = city_salaries.sort_values('Avg Salary', ascending=False)
            st.dataframe(city_salaries, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Top Paying Locations")
            fig = px.bar(
                city_salaries.head(10),
                x='City',
                y='Avg Salary',
                title="Average Salary by City"
            )
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

elif page == "Market Intelligence":
    st.header("🧠 Market Intelligence Dashboard")
    
    market_data = get_market_data()
    jobs = get_jobs()
    
    if market_data and jobs:
        df_market = pd.DataFrame(market_data)
        df_jobs = pd.DataFrame(jobs)
        
        # Market overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Markets Analyzed", len(df_market))
        with col2:
            avg_growth = df_market['tech_job_growth'].mean()
            st.metric("Avg Job Growth", f"{avg_growth:.1f}%")
        with col3:
            avg_col = df_market['cost_of_living_index'].mean()
            st.metric("Avg COL Index", f"{avg_col:.0f}")
        with col4:
            avg_commute = df_market['avg_commute_time'].mean()
            st.metric("Avg Commute", f"{avg_commute:.0f} min")
        
        # Market comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💼 Job Growth vs Cost of Living")
            fig = px.scatter(
                df_market,
                x='cost_of_living_index',
                y='tech_job_growth',
                size='startup_density',
                color='city',
                title="Market Opportunity Analysis",
                labels={
                    'cost_of_living_index': 'Cost of Living Index',
                    'tech_job_growth': 'Tech Job Growth (%)'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🚗 Commute vs Startup Density")
            fig = px.scatter(
                df_market,
                x='avg_commute_time',
                y='startup_density',
                color='city',
                title="Work-Life Balance Analysis"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Market ranking
        st.subheader("🏆 Market Rankings")
        
        # Calculate composite score
        df_market['opportunity_score'] = (
            df_market['tech_job_growth'] * 0.4 +
            (200 - df_market['cost_of_living_index']) * 0.3 +
            df_market['startup_density'] / 10 * 0.3
        )
        
        rankings = df_market.sort_values('opportunity_score', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(
                rankings[['city', 'tech_job_growth', 'cost_of_living_index', 'opportunity_score']].round(2),
                use_container_width=True
            )
        
        with col2:
            fig = px.bar(
                rankings.head(8),
                x='city',
                y='opportunity_score',
                title="Market Opportunity Score"
            )
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

elif page == "Job Alerts & Notifications":
    st.header("🔔 Job Alerts & Notifications")
    
    # User email input (in real app, this would be from authentication)
    if 'user_email' not in st.session_state:
        st.session_state.user_email = "demo@example.com"
    
    user_email = st.text_input("Your Email", value=st.session_state.user_email, key="user_email_input")
    st.session_state.user_email = user_email
    
    tab1, tab2, tab3 = st.tabs(["📍 Geofence Alerts", "💰 Salary Alerts", "🔔 Notifications"])
    
    with tab1:
        st.subheader("Set Up Geofence Alerts")
        st.markdown("Get notified when jobs are posted in specific areas")
        
        col1, col2 = st.columns([2, 1])
        
        with col2:
            with st.form("geofence_alert_form"):
                st.markdown("**Create New Alert**")
                
                alert_name = st.text_input("Alert Name", placeholder="e.g., SF Bay Area Jobs")
                location_input = st.text_input("Location", placeholder="San Francisco, CA")
                
                if st.form_submit_button("📍 Use This Location"):
                    lat, lon = geocode_location(location_input)
                    if lat and lon:
                        st.session_state.alert_lat = lat
                        st.session_state.alert_lng = lon
                        st.success(f"Location set: {lat:.4f}, {lon:.4f}")
                    else:
                        st.error("Could not geocode location")
                
                alert_lat = st.number_input("Latitude", 
                                           value=st.session_state.get('alert_lat', 37.7749), 
                                           format="%.4f")
                alert_lng = st.number_input("Longitude", 
                                           value=st.session_state.get('alert_lng', -122.4194), 
                                           format="%.4f")
                alert_radius = st.slider("Radius (km)", 1, 100, 25)
                
                alert_category = st.selectbox("Category Filter (Optional)", 
                                             ["All", "Software", "Data Science", "DevOps", "Security"])
                alert_min_salary = st.number_input("Minimum Salary (Optional)", 
                                                   min_value=0, value=0, step=10000)
                
                submit_geofence = st.form_submit_button("✅ Create Geofence Alert")
                
                if submit_geofence and alert_name and user_email:
                    alert_data = {
                        "user_email": user_email,
                        "alert_name": alert_name,
                        "alert_type": "geofence",
                        "center_lat": alert_lat,
                        "center_lng": alert_lng,
                        "radius_km": alert_radius,
                        "category": None if alert_category == "All" else alert_category,
                        "min_salary": alert_min_salary if alert_min_salary > 0 else None,
                        "location_name": location_input
                    }
                    create_alert(alert_data)
                    st.success(f"✅ Alert '{alert_name}' created!")
                    st.rerun()
        
        with col1:
            # Display map with geofence
            st.markdown("**Your Geofence Area**")
            m = folium.Map(
                location=[st.session_state.get('alert_lat', 37.7749), 
                         st.session_state.get('alert_lng', -122.4194)], 
                zoom_start=8
            )
            
            # Add circle for the geofence
            folium.Circle(
                [st.session_state.get('alert_lat', 37.7749), 
                 st.session_state.get('alert_lng', -122.4194)],
                radius=25000,  # 25km in meters
                color='red',
                fillColor='red',
                fillOpacity=0.2,
                popup="Alert Geofence"
            ).add_to(m)
            
            st_folium(m, width=600, height=400)
        
        # Display existing geofence alerts
        st.markdown("---")
        st.subheader("📋 Your Active Geofence Alerts")
        
        user_alerts = get_user_alerts(user_email)
        geofence_alerts = [a for a in user_alerts if a.get('alert_type') == 'geofence']
        
        if geofence_alerts:
            for alert in geofence_alerts:
                with st.expander(f"📍 {alert['alert_name']} - {alert.get('location_name', 'Unknown')}"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Location:** {alert['center_lat']:.4f}, {alert['center_lng']:.4f}")
                        st.write(f"**Radius:** {alert['radius_km']} km")
                    
                    with col2:
                        st.write(f"**Category:** {alert.get('category', 'All')}")
                        st.write(f"**Min Salary:** ${alert.get('min_salary', 0):,}")
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_geo_{alert['_id']}"):
                            delete_alert(alert['_id'])
                            st.success("Alert deleted!")
                            st.rerun()
                    
                    # Check for matches
                    if st.button(f"🔍 Check Now", key=f"check_geo_{alert['_id']}"):
                        matches = check_geofence_alerts(alert)
                        if matches:
                            st.success(f"Found {len(matches)} matching jobs!")
                            df = pd.DataFrame(matches)
                            st.dataframe(df[['title', 'company', 'location', 'salary']], use_container_width=True)
                        else:
                            st.info("No new jobs matching your criteria")
        else:
            st.info("No geofence alerts yet. Create one above!")
    
    with tab2:
        st.subheader("💰 Salary Increase Alerts")
        st.markdown("Get notified when average salaries increase in your target area")
        
        with st.form("salary_alert_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                salary_alert_name = st.text_input("Alert Name", placeholder="e.g., SF Salary Watch")
                salary_location = st.text_input("Location", placeholder="San Francisco, CA")
                
                if st.form_submit_button("📍 Set Location"):
                    lat, lon = geocode_location(salary_location)
                    if lat and lon:
                        st.session_state.salary_alert_lat = lat
                        st.session_state.salary_alert_lng = lon
                        st.success(f"Location set!")
            
            with col2:
                salary_alert_lat = st.number_input("Latitude", 
                                                   value=st.session_state.get('salary_alert_lat', 37.7749), 
                                                   format="%.4f", key="sal_lat")
                salary_alert_lng = st.number_input("Longitude", 
                                                   value=st.session_state.get('salary_alert_lng', -122.4194), 
                                                   format="%.4f", key="sal_lng")
                salary_alert_radius = st.slider("Radius (km)", 1, 100, 25, key="sal_radius")
                target_salary = st.number_input("Target Average Salary", 
                                               min_value=50000, value=120000, step=10000)
            
            submit_salary = st.form_submit_button("✅ Create Salary Alert")
            
            if submit_salary and salary_alert_name and user_email:
                alert_data = {
                    "user_email": user_email,
                    "alert_name": salary_alert_name,
                    "alert_type": "salary_increase",
                    "center_lat": salary_alert_lat,
                    "center_lng": salary_alert_lng,
                    "radius_km": salary_alert_radius,
                    "target_salary": target_salary,
                    "location_name": salary_location
                }
                create_alert(alert_data)
                st.success(f"✅ Salary alert '{salary_alert_name}' created!")
                st.rerun()
        
        # Display existing salary alerts
        st.markdown("---")
        st.subheader("📋 Your Active Salary Alerts")
        
        salary_alerts = [a for a in user_alerts if a.get('alert_type') == 'salary_increase']
        
        if salary_alerts:
            for alert in salary_alerts:
                with st.expander(f"💰 {alert['alert_name']} - Target: ${alert.get('target_salary', 0):,}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Location:** {alert.get('location_name', 'Unknown')}")
                        st.write(f"**Radius:** {alert['radius_km']} km")
                        st.write(f"**Target Avg Salary:** ${alert.get('target_salary', 0):,}")
                    
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_sal_{alert['_id']}"):
                            delete_alert(alert['_id'])
                            st.success("Alert deleted!")
                            st.rerun()
                    
                    # Check for salary increases
                    if st.button(f"🔍 Check Now", key=f"check_sal_{alert['_id']}"):
                        results = check_salary_increase_alerts(alert)
                        if results:
                            for result in results:
                                st.success(result['message'])
                                st.write(f"Based on {result['job_count']} recent jobs")
                        else:
                            st.info("Average salary hasn't reached target yet")
        else:
            st.info("No salary alerts yet. Create one above!")
    
    with tab3:
        st.subheader("🔔 Recent Notifications")
        
        notifications = get_user_notifications(user_email, limit=20)
        
        if notifications:
            for notif in notifications:
                read_status = "✅" if notif.get('is_read') else "🔴"
                with st.expander(f"{read_status} {notif.get('message', 'Notification')} - {notif['created_at'].strftime('%Y-%m-%d %H:%M')}"):
                    st.json(notif.get('data', {}))
                    
                    if not notif.get('is_read'):
                        if st.button("Mark as Read", key=f"read_{notif['_id']}"):
                            mark_notification_read(notif['_id'])
                            st.rerun()
        else:
            st.info("No notifications yet. Create some alerts to start receiving notifications!")
        
        # Simulate checking all alerts
        st.markdown("---")
        if st.button("🔄 Check All Alerts Now"):
            with st.spinner("Checking all your alerts..."):
                total_matches = 0
                
                for alert in user_alerts:
                    if alert.get('alert_type') == 'geofence':
                        matches = check_geofence_alerts(alert)
                        if matches:
                            total_matches += len(matches)
                            save_alert_notification(
                                user_email, 
                                alert['_id'],
                                {
                                    'type': 'new_jobs',
                                    'message': f"{len(matches)} new jobs in {alert['alert_name']}",
                                    'job_count': len(matches),
                                    'jobs': [{'title': j['title'], 'company': j['company'], 'salary': j['salary']} for j in matches[:5]]
                                }
                            )
                    
                    elif alert.get('alert_type') == 'salary_increase':
                        results = check_salary_increase_alerts(alert)
                        if results:
                            save_alert_notification(
                                user_email,
                                alert['_id'],
                                results[0]
                            )
                
                if total_matches > 0:
                    st.success(f"✅ Found {total_matches} total matches! Check notifications above.")
                else:
                    st.info("No new matches found at this time.")
                
                st.rerun()

elif page == "Add Job":
    st.header("➕ Add New Job")
    
    with st.form("job_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Job Title*")
            company = st.text_input("Company*")
            location = st.text_input("Location (City, State)*")
            salary = st.number_input("Salary ($)", min_value=0, value=80000)
            remote_friendly = st.checkbox("Remote Friendly")
        
        with col2:
            job_type = st.selectbox("Job Type", ["Full-time", "Part-time", "Contract", "Remote"])
            category = st.selectbox("Category", ["Software", "Data Science", "DevOps", "Security", "Design"])
            experience = st.selectbox("Experience Level", ["Entry", "Mid", "Senior"])
            posted_date = st.date_input("Posted Date", value=date.today())
        
        description = st.text_area("Job Description")
        requirements = st.text_area("Requirements")
        
        submitted = st.form_submit_button("🚀 Add Job")
        
        if submitted:
            if title and company and location:
                lat, lon = geocode_location(location)
                
                if lat and lon:
                    job_data = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "coordinates": [lon, lat],
                        "salary": salary,
                        "job_type": job_type,
                        "category": category,
                        "experience": experience,
                        "remote_friendly": remote_friendly,
                        "description": description,
                        "requirements": requirements,
                        "posted_date": posted_date.isoformat(),
                        "created_at": datetime.now()
                    }
                    
                    add_job(job_data)
                    st.success("✅ Job added successfully with coordinates!")
                    st.rerun()
                else:
                    st.error("❌ Could not geocode location. Please check the address.")
            else:
                st.error("❌ Please fill in all required fields (*)")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**🌍 Advanced GIS Job Portal**")
st.sidebar.markdown("*MongoDB + Streamlit + Advanced Geospatial Analytics*")