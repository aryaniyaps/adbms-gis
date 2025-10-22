import streamlit as st
import pymongo
import folium
from streamlit_folium import st_folium
import pandas as pd
from geopy.geocoders import Nominatim
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np
from sklearn.cluster import DBSCAN
import json

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
    "Add Job"
])

if page == "Interactive Job Map":
    st.header("🎯 Interactive Job Map with Clustering")
    
    jobs = get_jobs()
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
            
            if st.button("Search Jobs"):
                jobs = spatial_query_jobs(search_lat, search_lng, radius)
                st.success(f"Found {len(jobs)} jobs within {radius}km")
        
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