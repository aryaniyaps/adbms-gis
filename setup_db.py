import pymongo
from datetime import datetime, date
import random
import numpy as np
from shapely.geometry import Point, Polygon, LineString
import json

def setup_database():
    client = pymongo.MongoClient("mongodb://user:pass@localhost:27018/?directConnection=true")
    db = client.job_portal
    
    # Clear existing data
    for collection in ['jobs', 'tech_hubs', 'commute_routes', 'salary_zones', 'market_analysis']:
        db[collection].drop()
    
    # Generate 100+ jobs with realistic coordinates
    cities = [
        {"name": "San Francisco", "lat": 37.7749, "lng": -122.4194, "tech_multiplier": 1.8},
        {"name": "New York", "lat": 40.7128, "lng": -74.0060, "tech_multiplier": 1.6},
        {"name": "Seattle", "lat": 47.6062, "lng": -122.3321, "tech_multiplier": 1.7},
        {"name": "Austin", "lat": 30.2672, "lng": -97.7431, "tech_multiplier": 1.4},
        {"name": "Boston", "lat": 42.3601, "lng": -71.0589, "tech_multiplier": 1.5},
        {"name": "Los Angeles", "lat": 34.0522, "lng": -118.2437, "tech_multiplier": 1.3},
        {"name": "Chicago", "lat": 41.8781, "lng": -87.6298, "tech_multiplier": 1.2},
        {"name": "Denver", "lat": 39.7392, "lng": -104.9903, "tech_multiplier": 1.3}
    ]
    
    job_titles = ["Software Engineer", "Data Scientist", "Product Manager", "DevOps Engineer", 
                  "Frontend Developer", "Backend Developer", "ML Engineer", "Security Engineer"]
    companies = ["TechCorp", "DataFlow", "CloudSys", "AILabs", "WebSolutions", "CyberGuard"]
    
    jobs = []
    for i in range(120):
        city = random.choice(cities)
        # Add some spatial variance within city
        lat_offset = random.uniform(-0.1, 0.1)
        lng_offset = random.uniform(-0.1, 0.1)
        
        base_salary = random.randint(70000, 200000)
        adjusted_salary = int(base_salary * city["tech_multiplier"])
        
        job = {
            "title": random.choice(job_titles),
            "company": random.choice(companies),
            "location": city["name"],
            "coordinates": [city["lng"] + lng_offset, city["lat"] + lat_offset],
            "salary": adjusted_salary,
            "job_type": random.choice(["Full-time", "Contract", "Remote"]),
            "category": random.choice(["Software", "Data Science", "DevOps", "Security"]),
            "experience": random.choice(["Entry", "Mid", "Senior"]),
            "remote_friendly": random.choice([True, False]),
            "posted_date": f"2024-01-{random.randint(1, 30):02d}",
            "created_at": datetime.now()
        }
        jobs.append(job)
    
    db.jobs.insert_many(jobs)
    
    # Tech hub polygons
    tech_hubs = [
        {
            "name": "Silicon Valley",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-122.5, 37.3], [-122.0, 37.3], [-122.0, 37.8], [-122.5, 37.8], [-122.5, 37.3]]]
            },
            "avg_salary": 180000,
            "job_density": "high"
        },
        {
            "name": "Seattle Tech Corridor",
            "geometry": {
                "type": "Polygon", 
                "coordinates": [[[-122.4, 47.5], [-122.2, 47.5], [-122.2, 47.7], [-122.4, 47.7], [-122.4, 47.5]]]
            },
            "avg_salary": 160000,
            "job_density": "high"
        }
    ]
    db.tech_hubs.insert_many(tech_hubs)
    
    # Commute routes (LineStrings)
    routes = [
        {
            "from": "Suburb A",
            "to": "San Francisco Downtown",
            "geometry": {
                "type": "LineString",
                "coordinates": [[-122.5, 37.4], [-122.45, 37.45], [-122.4, 37.78]]
            },
            "commute_time": 45,
            "transport_mode": "car"
        }
    ]
    db.commute_routes.insert_many(routes)
    
    # Salary heat zones
    salary_zones = []
    for city in cities:
        for radius in [0.05, 0.1, 0.15]:  # Different zones
            zone = {
                "city": city["name"],
                "center": [city["lng"], city["lat"]],
                "radius_km": radius * 111,  # Convert to km
                "avg_salary": int(random.uniform(80000, 200000) * city["tech_multiplier"]),
                "job_count": random.randint(10, 50)
            }
            salary_zones.append(zone)
    db.salary_zones.insert_many(salary_zones)
    
    # Market analysis data
    market_data = []
    for city in cities:
        data = {
            "city": city["name"],
            "coordinates": [city["lng"], city["lat"]],
            "cost_of_living_index": random.uniform(90, 180),
            "tech_job_growth": random.uniform(5, 25),
            "startup_density": random.randint(50, 500),
            "avg_commute_time": random.randint(25, 60)
        }
        market_data.append(data)
    db.market_analysis.insert_many(market_data)
    
    # Create advanced indexes
    db.jobs.create_index([("coordinates", "2dsphere")])
    db.tech_hubs.create_index([("geometry", "2dsphere")])
    db.commute_routes.create_index([("geometry", "2dsphere")])
    db.salary_zones.create_index([("center", "2dsphere")])
    db.market_analysis.create_index([("coordinates", "2dsphere")])
    
    print(f"Advanced GIS database setup complete!")
    print(f"- {len(jobs)} jobs with precise coordinates")
    print(f"- {len(tech_hubs)} tech hub polygons")
    print(f"- {len(routes)} commute routes")
    print(f"- {len(salary_zones)} salary zones")
    print(f"- {len(market_data)} market analysis points")
    print("All collections have 2dsphere indexes for advanced geospatial queries.")

if __name__ == "__main__":
    setup_database()