"""
Rejseplanen API Demo and Visualization
"""

import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from main import (
    RejseplanenAPI, 
    LocationType, 
    ProductClass, 
    TransportMode, 
    Trip, 
    CommonData,
    TransportRequestType
)


def plot_trips(trips: List[Trip], common_data: CommonData, max_trips: int = 3):
    """
    Visualize trips using matplotlib with proper walking route support
    """
    n_trips = min(len(trips), max_trips)
    if n_trips == 0:
        print("No trips to plot")
        return None
    
    fig, axes = plt.subplots(1, n_trips, figsize=(6*n_trips, 8))
    if n_trips == 1:
        axes = [axes]
    
    for trip_idx, trip in enumerate(trips[:n_trips]):
        ax = axes[trip_idx]
        
        # Format title with service days
        title = f"Trip {trip_idx + 1}\n"
        title += f"Duration: {trip.duration[:2]}:{trip.duration[2:4]}\n"
        title += f"Changes: {trip.changes}"
        if trip.service_days and trip.service_days.regular:
            title += f"\n{trip.service_days.regular}"
        ax.set_title(title)
        
        all_coords = []
        legend_added = {'walking': False, 'transit': False}
        
        for section in trip.sections:
            # Handle journey sections (train/bus/metro)
            if section.journey and section.journey.polyline_indices:
                for poly_idx in section.journey.polyline_indices:
                    if poly_idx in common_data.polylines:
                        polyline = common_data.polylines[poly_idx]
                        if polyline.coordinates:
                            lats = [c.lat for c in polyline.coordinates]
                            lons = [c.lon for c in polyline.coordinates]
                            all_coords.extend(polyline.coordinates)
                            
                            # Get product info for color and label
                            color = 'red'
                            label = None
                            if section.journey.product_index is not None:
                                prod = common_data.products.get(section.journey.product_index)
                                if prod:
                                    if 'Metro' in prod.name:
                                        if 'M1' in prod.name:
                                            color = '#00A84F'  # Green for M1
                                        else:
                                            color = '#FFC80A'  # Yellow for M2
                                        label = prod.name
                                    elif 'S-Tog' in str(prod.category_out):
                                        color = '#F68B1F'  # Orange for S-train
                                        label = prod.name
                                    elif 'Bus' in str(prod.category_out):
                                        color = '#FDB913'  # Yellow for bus
                                        label = prod.name
                                    else:
                                        label = 'Transit' if not legend_added['transit'] else None
                                        legend_added['transit'] = True
                            
                            ax.plot(lons, lats, color=color, linewidth=3, 
                                   alpha=0.8, label=label)
            
            # Handle walking sections - check for polyline in GIS info
            elif section.type == TransportMode.WALK and section.gis:
                plotted = False
                
                # First check if polyline was fetched and stored
                if section.gis.polyline and section.gis.polyline.coordinates:
                    lats = [c.lat for c in section.gis.polyline.coordinates]
                    lons = [c.lon for c in section.gis.polyline.coordinates]
                    all_coords.extend(section.gis.polyline.coordinates)
                    ax.plot(lons, lats, 'b--', linewidth=2, alpha=0.7, 
                           label='Walking' if not legend_added['walking'] else None)
                    legend_added['walking'] = True
                    plotted = True
                    
                    # Add distance annotation
                    if section.gis.distance and len(lons) > 1:
                        mid_idx = len(lons) // 2
                        ax.annotate(f"{section.gis.distance}m", 
                                  xy=(lons[mid_idx], lats[mid_idx]),
                                  fontsize=8, color='blue',
                                  bbox=dict(boxstyle='round,pad=0.3', 
                                          facecolor='white', alpha=0.7))
                
                # Check if it's in the walking_polylines cache
                elif section.gis.ctx in common_data.walking_polylines:
                    polyline = common_data.walking_polylines[section.gis.ctx]
                    if polyline.coordinates:
                        lats = [c.lat for c in polyline.coordinates]
                        lons = [c.lon for c in polyline.coordinates]
                        all_coords.extend(polyline.coordinates)
                        ax.plot(lons, lats, 'b--', linewidth=2, alpha=0.7,
                               label='Walking' if not legend_added['walking'] else None)
                        legend_added['walking'] = True
                        plotted = True
                        
                        # Add distance annotation
                        if section.gis.distance and len(lons) > 1:
                            mid_idx = len(lons) // 2
                            ax.annotate(f"{section.gis.distance}m", 
                                      xy=(lons[mid_idx], lats[mid_idx]),
                                      fontsize=8, color='blue',
                                      bbox=dict(boxstyle='round,pad=0.3', 
                                              facecolor='white', alpha=0.7))
                
                # Fallback to straight line between endpoints
                if not plotted:
                    from_loc = None
                    to_loc = None
                    if section.departure and 'locX' in section.departure:
                        from_loc = common_data.locations.get(section.departure['locX'])
                    if section.arrival and 'locX' in section.arrival:
                        to_loc = common_data.locations.get(section.arrival['locX'])
                    
                    if from_loc and to_loc:
                        ax.plot([from_loc.coordinate.lon, to_loc.coordinate.lon],
                               [from_loc.coordinate.lat, to_loc.coordinate.lat],
                               'b:', linewidth=1, alpha=0.5,
                               label='Walking (approx)' if not legend_added['walking'] else None)
                        legend_added['walking'] = True
                        all_coords.extend([from_loc.coordinate, to_loc.coordinate])
                        
                        # Add distance annotation
                        if section.gis.distance:
                            mid_lon = (from_loc.coordinate.lon + to_loc.coordinate.lon) / 2
                            mid_lat = (from_loc.coordinate.lat + to_loc.coordinate.lat) / 2
                            ax.annotate(f"{section.gis.distance}m (straight line)", 
                                      xy=(mid_lon, mid_lat),
                                      fontsize=7, color='blue', style='italic',
                                      bbox=dict(boxstyle='round,pad=0.3', 
                                              facecolor='yellow', alpha=0.5))
            
            # Plot endpoints as markers
            if section.departure and 'locX' in section.departure:
                loc_idx = section.departure['locX']
                if loc_idx in common_data.locations:
                    loc = common_data.locations[loc_idx]
                    if trip_idx == 0 and section == trip.sections[0]:  # Start point
                        ax.scatter(loc.coordinate.lon, loc.coordinate.lat, 
                                 c='green', s=150, zorder=5, marker='o',
                                 edgecolors='black', linewidth=2, label='Start')
                    else:
                        ax.scatter(loc.coordinate.lon, loc.coordinate.lat, 
                                 c='orange', s=80, zorder=4, marker='o',
                                 edgecolors='black', linewidth=1)
                    all_coords.append(loc.coordinate)
            
            if section.arrival and 'locX' in section.arrival:
                loc_idx = section.arrival['locX']
                if loc_idx in common_data.locations:
                    loc = common_data.locations[loc_idx]
                    if trip_idx == 0 and section == trip.sections[-1]:  # End point
                        ax.scatter(loc.coordinate.lon, loc.coordinate.lat, 
                                 c='red', s=150, zorder=5, marker='s',
                                 edgecolors='black', linewidth=2, label='End')
                    else:
                        ax.scatter(loc.coordinate.lon, loc.coordinate.lat, 
                                 c='orange', s=80, zorder=4, marker='s',
                                 edgecolors='black', linewidth=1)
                    all_coords.append(loc.coordinate)
        
        # Set axis limits with proper margins
        if all_coords:
            lats = [c.lat for c in all_coords]
            lons = [c.lon for c in all_coords]
            lat_margin = (max(lats) - min(lats)) * 0.15 or 0.002
            lon_margin = (max(lons) - min(lons)) * 0.15 or 0.002
            ax.set_xlim(min(lons) - lon_margin, max(lons) + lon_margin)
            ax.set_ylim(min(lats) - lat_margin, max(lats) + lat_margin)
        
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal', adjustable='box')
        
        # Add legend
        ax.legend(loc='best', fontsize=8, framealpha=0.9)
    
    plt.suptitle('Rejseplanen Routes', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def print_trip_summary(trip: Trip, common_data: CommonData):
    """Print a concise summary of a trip"""
    duration_min = int(trip.duration[:2]) * 60 + int(trip.duration[2:4])
    print(f"  Duration: {duration_min} min, Changes: {trip.changes}")
    
    for section in trip.sections:
        if section.type == TransportMode.WALK:
            dist = section.gis.distance if section.gis else 0
            has_poly = bool(section.gis and (section.gis.polyline or 
                          section.gis.ctx in common_data.walking_polylines))
            print(f"    • Walk {dist}m {'(GPS route)' if has_poly else '(straight line)'}")
        elif section.journey and section.journey.product_index is not None:
            prod = common_data.products.get(section.journey.product_index)
            if prod:
                print(f"    • {prod.name} → {section.journey.direction_text or 'Unknown'}")


def main():
    """Main demo function"""
    print("=== Rejseplanen Complete API Demo ===\n")
    
    # Initialize API with auto-fetching of walking routes
    api = RejseplanenAPI(debug=False, auto_fetch_walking=True)
    
    # Test location search
    print("1. Testing location search...")
    test_location = "Flintholm"
    locations = api.search_location(test_location, LocationType.STATION)
    print(f"Found {len(locations)} locations for '{test_location}':")
    for loc in locations[:3]:
        print(f"  - {loc.name} ({loc.type}): {loc.coordinate.lat:.6f}, {loc.coordinate.lon:.6f}")
    
    # Test trip planning with all features
    print("\n2. Testing comprehensive trip planning...")
    origin = input("Enter origin (default: Nørreport): ").strip() or "Nørreport"
    destination = input("Enter destination (default: Flintholm): ").strip() or "Flintholm"
    
    print(f"\nSearching for trips from {origin} to {destination}...")
    trips, common_data, full_response = api.plan_trip(
        origin=origin,
        destination=destination,
        products=ProductClass.ALL,
        get_polylines=True,
        get_passlist=True,
        get_tariff=True,
        max_walk_distance=2000
    )
    
    if trips:
        print(f"\nFound {len(trips)} trips:")
        for i, trip in enumerate(trips[:5], 1):
            print(f"\nTrip {i}:")
            print_trip_summary(trip, common_data)
        
        # Print detailed info for first trip
        if input("\nShow detailed trip info? (y/n): ").lower() == 'y':
            api.print_trip_details(trips[0], common_data)
        
        # Check walking polyline fetching
        print("\n3. Checking walking route data...")
        walking_count = 0
        for trip in trips:
            for section in trip.sections:
                if section.type == TransportMode.WALK and section.gis:
                    if section.gis.polyline or section.gis.ctx in common_data.walking_polylines:
                        walking_count += 1
        print(f"Found {walking_count} walking segments with GPS polylines")
        
        # Test manual walking detail fetching
        print("\n4. Testing manual walking route details...")
        for trip in trips[:1]:
            for section in trip.sections[:1]:
                if section.type == TransportMode.WALK and section.gis and section.gis.ctx:
                    print(f"Fetching details for walking segment ({section.gis.distance}m)...")
                    coords, segments, polyline = api.get_walking_details(section.gis.ctx)
                    if polyline:
                        print(f"  GPS points: {len(polyline.coordinates)}")
                        print(f"  Turn-by-turn segments: {len(segments)}")
                        for seg in segments[:3]:
                            if seg.instruction:
                                print(f"    - {seg.instruction}: {seg.distance}m {seg.orientation or ''}")
                    break
        
        # Check for service messages
        if common_data.remarks:
            print("\n5. Service messages:")
            for msg in common_data.remarks[:5]:
                print(f"  - [{msg.code}] {msg.text}")
        
        # Check connection groups
        if 'outConGrpL' in full_response:
            print("\n6. Available transport mode groups:")
            for grp in full_response['outConGrpL']:
                print(f"  - {grp['name']} ({grp['grpid']})")
        
        # Plot trips
        print("\n7. Plotting trips with walking routes...")
        fig = plot_trips(trips, common_data)
        if fig:
            plt.show()
            
            # Save plot
            filename = f'rejseplanen_{origin.lower()}_{destination.lower()}.png'
            fig.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"Plot saved as '{filename}'")
        
        # Test pagination if available
        if full_response.get('outCtxScrF'):
            if input("\n8. Load more trips? (y/n): ").lower() == 'y':
                print("Fetching more trips...")
                more_trips, more_common = api.scroll_trips(full_response['outCtxScrF'], "F", 3)
                print(f"Found {len(more_trips)} additional trips")
                for i, trip in enumerate(more_trips, len(trips)+1):
                    print(f"\nTrip {i}:")
                    print_trip_summary(trip, more_common)
    else:
        print("No trips found")
    
    # Test polyline decoding
    print("\n9. Testing polyline decoder...")
    test_polylines = [
        "kuzrIqyjkAmCzWoD`YqC`^",  # From your data
        "ykzrIorikA???UFqCJcDP}H@]H_F@a@?YGISOy@k@mBuAsA}@u@g@q@c@Ho@TLB@BW?G@?ADB@B[AA"  # Walking route
    ]
    for encoded in test_polylines[:1]:
        decoded = api.decode_polyline(encoded)
        print(f"Decoded {len(decoded)} coordinates from polyline")
        if decoded:
            print(f"  First: ({decoded[0][0]:.6f}, {decoded[0][1]:.6f})")
            print(f"  Last: ({decoded[-1][0]:.6f}, {decoded[-1][1]:.6f})")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
