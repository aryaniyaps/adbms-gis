# 🌍 Advanced ADBMS-GIS Job Portal

A sophisticated Streamlit application showcasing advanced MongoDB geospatial capabilities with comprehensive GIS analysis for job market intelligence.

## 🚀 Advanced Features

### 🗺️ Geospatial Analytics

- **Multi-layer Mapping**: Interactive maps with job clusters, tech hub polygons, and salary zones
- **Spatial Queries**: MongoDB 2dsphere indexing for complex geometric queries
- **DBSCAN Clustering**: Machine learning-based job clustering analysis
- **Radius Search**: Find jobs within specified distances using spherical geometry

### 📊 Market Intelligence

- **Salary Heatmaps**: Visualize compensation patterns across geographic regions
- **Tech Hub Analysis**: Polygon-based analysis of technology corridors
- **Commute Accessibility**: Distance-based job accessibility analysis
- **Market Opportunity Scoring**: Multi-factor analysis combining growth, cost, and density

### 🔬 Advanced GIS Operations

- **Polygon Containment**: Jobs within tech hub boundaries
- **Nearest Neighbor**: Find closest opportunities to any location
- **Gradient Analysis**: Salary trends by distance from city centers
- **Density Calculations**: Job concentration per square kilometer

## 🛠️ Tech Stack

- **Frontend**: Streamlit with Folium for advanced mapping
- **Database**: MongoDB with 2dsphere geospatial indexing
- **GIS Libraries**: Shapely, GeoPandas for geometric operations
- **ML**: Scikit-learn for spatial clustering (DBSCAN)
- **Visualization**: Plotly for interactive charts and 3D analysis
- **Geocoding**: Geopy with Nominatim for coordinate resolution

## 📋 Prerequisites

- Python 3.13
- UV Package Manager
- Docker Compose

## ⚡ Quick Setup

1. **Install dependencies**:

   ```bash
   uv sync --python 3.13
   ```

2. **Start MongoDB with Docker Compose**:

   ```bash
   docker-compose up -d
   ```

3. **Initialize advanced GIS database**:

   ```bash
   uv run main.py setup
   ```

4. **Launch the application**:
   ```bash
   uv run main.py
   ```

## 🎯 Application Features

### 1. Interactive Job Map

- **Clustering Visualization**: DBSCAN-based job clustering with color coding
- **Tech Hub Overlays**: Polygon visualization of technology corridors
- **Spatial Filtering**: Radius-based job search with real-time updates
- **Multi-layer Controls**: Toggle between different data layers

### 2. Spatial Analytics

- **Job Density Analysis**: Calculate jobs per square kilometer
- **Geographic Spread Metrics**: Quantify market distribution
- **Distance-based Analysis**: Nearest neighbor and accessibility studies
- **Cluster Statistics**: Detailed clustering analysis with DBSCAN

### 3. Salary Heatmap

- **Compensation Zones**: Circular salary zones with color coding
- **Geographic Salary Trends**: Visualize pay scales across regions
- **Statistical Analysis**: City-wise salary distributions and rankings

### 4. Market Intelligence

- **Opportunity Scoring**: Multi-factor market analysis
- **Growth vs Cost Analysis**: Scatter plots of market dynamics
- **Startup Ecosystem**: Density analysis of entrepreneurial activity
- **Commute Analysis**: Work-life balance metrics

### 5. Advanced Job Management

- **Geocoded Job Entry**: Automatic coordinate resolution
- **Spatial Validation**: Ensure geographic accuracy
- **Real-time Updates**: Live map updates with new entries

## 🗄️ Database Architecture

### Collections with 2dsphere Indexes:

```javascript
// Jobs Collection
{
  title: String,
  company: String,
  location: String,
  coordinates: [longitude, latitude], // GeoJSON Point
  salary: Number,
  job_type: String,
  category: String,
  experience: String,
  remote_friendly: Boolean,
  posted_date: String,
  created_at: Date
}

// Tech Hubs Collection (Polygons)
{
  name: String,
  geometry: {
    type: "Polygon",
    coordinates: [[[lng, lat], [lng, lat], ...]]
  },
  avg_salary: Number,
  job_density: String
}

// Salary Zones Collection (Circles)
{
  city: String,
  center: [longitude, latitude],
  radius_km: Number,
  avg_salary: Number,
  job_count: Number
}

// Market Analysis Collection
{
  city: String,
  coordinates: [longitude, latitude],
  cost_of_living_index: Number,
  tech_job_growth: Number,
  startup_density: Number,
  avg_commute_time: Number
}
```

## 🔍 Advanced GIS Queries

The application demonstrates sophisticated MongoDB geospatial operations:

- **$geoWithin**: Find jobs within polygons and circles
- **$near**: Nearest neighbor searches with distance limits
- **$centerSphere**: Spherical radius queries for accurate distance
- **$geoIntersects**: Geometric intersection analysis
- **2dsphere indexes**: Optimized for spherical geometry

## 🎨 Visualization Techniques

- **Choropleth Maps**: Color-coded regions by data density
- **Proportional Symbols**: Marker sizes based on salary values
- **Multi-layer Overlays**: Simultaneous display of multiple data types
- **Interactive Popups**: Detailed information on hover/click
- **Cluster Visualization**: Color-coded job groupings

## 🧮 Spatial Analysis Algorithms

- **DBSCAN Clustering**: Density-based spatial clustering
- **Voronoi Diagrams**: Market territory analysis
- **Buffer Analysis**: Proximity-based job accessibility
- **Gradient Analysis**: Spatial trend identification

This project showcases enterprise-level GIS capabilities suitable for:

- Urban planning applications
- Real estate market analysis
- Supply chain optimization
- Location intelligence platforms
- Demographic studies
