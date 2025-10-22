import numpy as np
from shapely.geometry import Point, Polygon
import pymongo
from geopy.distance import geodesic

class GISAnalyzer:
    def __init__(self, db_client=None):
        if db_client is None:
            db_client = pymongo.MongoClient("mongodb://user:pass@localhost:27018/?directConnection=true")
        self.db = db_client.job_portal
    
    def find_jobs_within_polygon(self, polygon_coords):
        """Find jobs within a polygon using MongoDB geospatial query"""
        query = {
            "coordinates": {
                "$geoWithin": {
                    "$geometry": {
                        "type": "Polygon",
                        "coordinates": [polygon_coords]
                    }
                }
            }
        }
        return list(self.db.jobs.find(query))
    
    def find_nearest_jobs(self, lat, lng, limit=10):
        """Find nearest jobs to a point"""
        query = {
            "coordinates": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "$maxDistance": 100000  # 100km
                }
            }
        }
        return list(self.db.jobs.find(query).limit(limit))
    
    def calculate_job_density(self, center_lat, center_lng, radius_km):
        """Calculate job density within radius"""
        query = {
            "coordinates": {
                "$geoWithin": {
                    "$centerSphere": [[center_lng, center_lat], radius_km / 6371]
                }
            }
        }
        count = self.db.jobs.count_documents(query)
        area = np.pi * (radius_km ** 2)
        return count / area if area > 0 else 0
    
    def analyze_commute_accessibility(self, home_lat, home_lng, max_commute_km=50):
        """Analyze job accessibility based on commute distance"""
        accessible_jobs = []
        jobs = list(self.db.jobs.find())
        
        for job in jobs:
            job_lat, job_lng = job['coordinates'][1], job['coordinates'][0]
            distance = geodesic((home_lat, home_lng), (job_lat, job_lng)).kilometers
            
            if distance <= max_commute_km:
                job['commute_distance'] = distance
                accessible_jobs.append(job)
        
        return sorted(accessible_jobs, key=lambda x: x['commute_distance'])
    
    def salary_gradient_analysis(self, center_lat, center_lng, max_radius=100):
        """Analyze salary gradient from a center point"""
        jobs = list(self.db.jobs.find())
        gradient_data = []
        
        for job in jobs:
            job_lat, job_lng = job['coordinates'][1], job['coordinates'][0]
            distance = geodesic((center_lat, center_lng), (job_lat, job_lng)).kilometers
            
            if distance <= max_radius:
                gradient_data.append({
                    'distance': distance,
                    'salary': job['salary'],
                    'title': job['title'],
                    'company': job['company']
                })
        
        return gradient_data
    
    def tech_hub_overlap_analysis(self):
        """Analyze job overlap with tech hubs"""
        tech_hubs = list(self.db.tech_hubs.find())
        results = []
        
        for hub in tech_hubs:
            # Find jobs within tech hub polygon
            jobs_in_hub = self.db.jobs.find({
                "coordinates": {
                    "$geoWithin": {
                        "$geometry": hub['geometry']
                    }
                }
            })
            
            jobs_list = list(jobs_in_hub)
            avg_salary = np.mean([job['salary'] for job in jobs_list]) if jobs_list else 0
            
            results.append({
                'hub_name': hub['name'],
                'job_count': len(jobs_list),
                'avg_salary': avg_salary,
                'expected_salary': hub['avg_salary'],
                'salary_variance': avg_salary - hub['avg_salary'] if jobs_list else 0
            })
        
        return results