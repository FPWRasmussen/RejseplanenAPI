"""
RejseplanenAPI - Complete Python wrapper for the Danish Rejseplanen API
License: MIT

Complete implementation with Plustur/Flextur (TETA) support and automatic walking route fetching.
"""

import requests
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum, IntFlag


# ============================================================================
# ENUMS AND FLAGS
# ============================================================================

class TransportMode(Enum):
    """Transport mode types"""
    WALK = "WALK"
    JNY = "JNY"   # Journey (train/bus/metro)
    BIKE = "BIKE"
    CAR = "CAR"
    TAXI = "TAXI"
    KISS = "KISS"  # Kiss & Ride
    PARK = "PARK"  # Park & Ride
    TETA = "TETA"  # Teletaxi/Plustur (dial-a-ride service)


class LocationType(Enum):
    """Location types for search"""
    STATION = "S"
    ADDRESS = "A"
    POI = "P"
    ALL = "ALL"
    COORDINATE = "C"


class ProductClass(IntFlag):
    """Product classes (bitmask)"""
    HIGH_SPEED_TRAIN = 1     # ICE, IC
    INTERCITY_TRAIN = 2      # IC, EC
    INTER_REGIONAL = 4       # IR
    REGIONAL = 8             # RE, RB
    METRO = 16               # S-Bahn
    BUS = 32                 # Bus
    BOAT = 64                # Boat
    SUBWAY = 128             # U-Bahn
    TRAM = 256               # Tram
    FLEXTUR = 256            # Flexible transport/Plustur
    TAXI = 512               # Taxi
    ALL = 4095               # All products


class TransportRequestType(Enum):
    """Available request types for multimodal transport"""
    WALK_PUBLIC = "RQ_WALK_OEV"
    BIKE_DONKEY_BACK = "RQ_BIKESH_DONKEY_BACK"
    BIKE_DONKEY_FRONT = "RQ_BIKESH_DONKEY_FRONT"
    BIKE_DONKEY_ONLY = "RQ_BIKESH_DONKEY_ONLY"
    CAR_GOMORE_ONLY = "RQ_CARPO_GOMORE_ONLY"
    CAR_NABOGO_FRONT = "RQ_CARPO_NABOGO_FRONT"
    CAR_NABOGO_BACK = "RQ_CARPO_NABOGO_BACK"
    CAR_NABOGO_ONLY = "RQ_CARPO_NABOGO_ONLY"
    CAR_FDM_FRONT = "RQ_CARPO_FDM_FRONT"
    CAR_FDM_BACK = "RQ_CARPO_FDM_BACK"
    CAR_FDM_ONLY = "RQ_CARPO_FDM_ONLY"


class MessageType(Enum):
    """Message types for service disruptions"""
    REMARK = "REM"
    HIM = "HIM"  # Hafas Information Manager
    ATTRIBUTE = "A"
    HEADER = "H"
    INFO = "I"


class MessageCode(Enum):
    """Common message codes"""
    BE = "BE"  # Barrier-free/Accessibility
    FR = "FR"  # Free (e.g., free bike transport)
    FB = "FB"  # Bicycle restrictions
    DELAY = "390"  # Delay information
    TELETAXI = "teletaxi"  # Plustur/Flextur booking required


class ScoringType(Enum):
    """Scoring types for trip ranking"""
    DEPARTURE = "DT"  # Departure time
    ARRIVAL = "AT"    # Arrival time
    COST = "CO"       # Cost/Price
    TIME = "TI"       # Duration


class RealtimeStatus(Enum):
    """Real-time status codes"""
    PLANNED = "P"      # Planned/Scheduled
    REALTIME = "R"     # Real-time
    CALCULATED = "C"   # Calculated
    CANCELLED = "X"    # Cancelled


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Coordinate:
    """GPS coordinate with layer and coordinate system info"""
    lat: float
    lon: float
    layer_index: int = 0
    crd_sys_index: int = 0
    
    @classmethod
    def from_api(cls, crd: Dict) -> 'Coordinate':
        """Create from API coordinate dictionary"""
        return cls(
            lat=crd.get('y', 0) / 1e6,
            lon=crd.get('x', 0) / 1e6,
            layer_index=crd.get('layerX', 0),
            crd_sys_index=crd.get('crdSysX', 0)
        )


@dataclass
class Color:
    """RGB color definition"""
    r: int
    g: int
    b: int
    
    def to_hex(self) -> str:
        """Convert to hex color string"""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


@dataclass
class Icon:
    """Icon definition with colors"""
    resource: str
    text: Optional[str] = None
    foreground: Optional[Color] = None
    background: Optional[Color] = None
    
    @classmethod
    def from_api(cls, data: Dict) -> 'Icon':
        """Create from API icon data"""
        fg = Color(**data['fg']) if 'fg' in data else None
        bg = Color(**data['bg']) if 'bg' in data else None
        return cls(
            resource=data.get('res', ''),
            text=data.get('txt'),
            foreground=fg,
            background=bg
        )


@dataclass
class DrawStyle:
    """Drawing style for map polylines"""
    type: str  # SOLID, DOT, DASH
    icon_index: Optional[int] = None
    background: Optional[Color] = None
    
    @classmethod
    def from_api(cls, data: Dict) -> 'DrawStyle':
        """Create from API draw style data"""
        bg = Color(**data['bg']) if 'bg' in data else None
        return cls(
            type=data.get('type', 'SOLID'),
            icon_index=data.get('sIcoX'),
            background=bg
        )


@dataclass
class Location:
    """Complete location with all metadata"""
    lid: str
    name: str
    type: str
    coordinate: Coordinate
    ext_id: Optional[str] = None
    state: str = "F"
    weight: int = 0
    is_main_mast: bool = False
    product_classes: int = 0
    product_refs: List[int] = field(default_factory=list)
    icon_index: Optional[int] = None
    house_number: Optional[str] = None
    
    @classmethod
    def from_api(cls, data: Dict) -> 'Location':
        """Create from API location data"""
        coord = Coordinate.from_api(data['crd']) if 'crd' in data else Coordinate(0, 0)
        return cls(
            lid=data.get('lid', ''),
            name=data.get('name', ''),
            type=data.get('type', ''),
            coordinate=coord,
            ext_id=data.get('extId'),
            state=data.get('state', 'F'),
            weight=data.get('wt', 0),
            is_main_mast=data.get('isMainMast', False),
            product_classes=data.get('pCls', 0),
            product_refs=data.get('pRefL', []),
            icon_index=data.get('icoX'),
            house_number=data.get('H')
        )


@dataclass
class Product:
    """Transport product with full details"""
    pid: Optional[str] = None
    name: str = ""
    name_short: Optional[str] = None
    number: Optional[str] = None
    line: Optional[str] = None
    line_id: Optional[str] = None
    category: Optional[str] = None
    category_out: Optional[str] = None
    category_code: Optional[str] = None
    cls: int = 0
    operator_index: Optional[int] = None
    admin: Optional[str] = None
    match_id: Optional[str] = None
    icon_index: Optional[int] = None
    him_ids: List[str] = field(default_factory=list)
    
    @classmethod
    def from_api(cls, data: Dict) -> 'Product':
        """Create from API product data"""
        ctx = data.get('prodCtx', {})
        return cls(
            pid=data.get('pid'),
            name=data.get('name', ''),
            name_short=data.get('nameS'),
            number=data.get('number') or ctx.get('num'),
            line=ctx.get('line'),
            line_id=ctx.get('lineId'),
            category=ctx.get('catIn'),
            category_out=ctx.get('catOut'),
            category_code=ctx.get('catCode'),
            cls=data.get('cls', 0),
            operator_index=data.get('oprX'),
            admin=ctx.get('admin'),
            match_id=ctx.get('matchId'),
            icon_index=data.get('icoX'),
            him_ids=data.get('himIdL', [])
        )


@dataclass
class Operator:
    """Transport operator"""
    name: str
    icon_index: Optional[int] = None


@dataclass
class ServiceDays:
    """Service days information"""
    regular: Optional[str] = None      # e.g., "lør, søn"
    irregular: Optional[str] = None    # e.g., "også 15. sep - 3. okt 2025"
    bitmask: Optional[str] = None      # Service day bitmask
    
    @classmethod
    def from_api(cls, data: Dict) -> 'ServiceDays':
        """Create from API service days data"""
        return cls(
            regular=data.get('sDaysR'),
            irregular=data.get('sDaysI'),
            bitmask=data.get('sDaysB')
        )


@dataclass
class ServiceMessage:
    """Service message/disruption/remark"""
    type: str
    code: Optional[str] = None
    priority: int = 0
    text: Optional[str] = None
    text_normal: Optional[str] = None
    icon_index: Optional[int] = None
    style: Optional[str] = None
    from_location_index: Optional[int] = None
    to_location_index: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    sort_order: int = 0
    rem_index: Optional[int] = None
    
    @classmethod
    def from_api(cls, data: Dict) -> 'ServiceMessage':
        """Create from API message data"""
        return cls(
            type=data.get('type', ''),
            code=data.get('code'),
            priority=data.get('prio', 0),
            text=data.get('txtN'),
            text_normal=data.get('txtS'),
            icon_index=data.get('icoX'),
            style=data.get('sty'),
            from_location_index=data.get('fLocX'),
            to_location_index=data.get('tLocX'),
            tags=data.get('tagL', []),
            sort_order=data.get('sort', 0),
            rem_index=data.get('remX')
        )


@dataclass
class WalkingSegment:
    """Detailed walking segment with turn-by-turn navigation"""
    name: Optional[str] = None
    instruction: Optional[str] = None
    orientation: Optional[str] = None
    route_type: Optional[str] = None
    distance: int = 0
    poly_start: int = 0
    poly_end: int = 0
    icon_index: Optional[int] = None
    
    @classmethod
    def from_api(cls, data: Dict) -> 'WalkingSegment':
        """Create from API segment data"""
        return cls(
            name=data.get('name'),
            instruction=data.get('manTx'),
            orientation=data.get('ori'),
            route_type=data.get('rType'),
            distance=data.get('dist', 0),
            poly_start=data.get('polyS', 0),
            poly_end=data.get('polyE', 0),
            icon_index=data.get('icoX')
        )


@dataclass
class Polyline:
    """Polyline with encoded coordinates and metadata"""
    encoded: str
    coordinates: List[Coordinate] = field(default_factory=list)
    location_refs: List[Dict[str, int]] = field(default_factory=list)
    draw_style_index: Optional[int] = None
    delta: bool = True
    dimension: int = 2
    encoding_start: Optional[str] = None
    encoding_format: Optional[str] = None


@dataclass
class Stop:
    """Stop along a journey"""
    location_index: int
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_platform: Optional[str] = None
    departure_platform: Optional[str] = None
    arrival_delay: Optional[int] = None
    departure_delay: Optional[int] = None
    cancelled: bool = False
    additional: bool = False
    
    @classmethod
    def from_api(cls, data: Dict) -> 'Stop':
        """Create from API stop data"""
        return cls(
            location_index=data.get('locX', -1),
            arrival_time=data.get('aTimeS'),
            departure_time=data.get('dTimeS'),
            arrival_platform=data.get('aPlatfS'),
            departure_platform=data.get('dPlatfS'),
            arrival_delay=data.get('aDelayS'),
            departure_delay=data.get('dDelayS'),
            cancelled=data.get('cancelled', False),
            additional=data.get('additional', False)
        )


@dataclass
class Journey:
    """Journey details for a transit section"""
    jid: str
    date: str
    product_index: Optional[int] = None
    direction_text: Optional[str] = None
    direction_flag: Optional[str] = None
    status: Optional[str] = None
    is_reachable: bool = True
    stops: List[Stop] = field(default_factory=list)
    polyline_indices: List[int] = field(default_factory=list)
    messages: List[ServiceMessage] = field(default_factory=list)
    subscription: str = "N"
    ctx_recon: Optional[str] = None


@dataclass
class GisInfo:
    """GIS information for walking/cycling sections"""
    distance: int
    duration_seconds: str
    ctx: str
    provider: str = "E"
    segments: List[WalkingSegment] = field(default_factory=list)
    polyline: Optional[Polyline] = None  # Store fetched polyline here


@dataclass
class TripSection:
    """Section of a trip (walking, transit, etc.)"""
    type: TransportMode
    departure: Optional[Dict[str, Any]] = None
    arrival: Optional[Dict[str, Any]] = None
    journey: Optional[Journey] = None
    gis: Optional[GisInfo] = None
    polyline_indices: List[int] = field(default_factory=list)
    messages: List[ServiceMessage] = field(default_factory=list)
    call_ahead_service: bool = False  # For Plustur
    booking_required: bool = False
    booking_deadline_minutes: Optional[int] = None


@dataclass
class FareSet:
    """Fare/ticket information"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    ticket_ids: List[str] = field(default_factory=list)


@dataclass
class TariffResult:
    """Tariff/fare calculation result"""
    status_code: str
    fare_sets: List[FareSet] = field(default_factory=list)
    external_content: Optional[Dict] = None
    messages: List[str] = field(default_factory=list)


@dataclass
class ConnectionScore:
    """Scoring for trip ranking"""
    score: int
    score_string: str
    connection_refs: List[int] = field(default_factory=list)


@dataclass
class ConnectionGroup:
    """Group of connections with scoring"""
    name: str
    group_id: str
    icon_index: Optional[int] = None
    scoring_types: List[Dict[str, Any]] = field(default_factory=list)
    initial_scoring_type: str = "DT"
    requests: List[Dict[str, Any]] = field(default_factory=list)
    scrollable: bool = False


@dataclass
class Trip:
    """Complete trip from origin to destination"""
    id: str
    date: str
    duration: str
    changes: int
    departure_time: str
    arrival_time: str
    sections: List[TripSection]
    service_days: Optional[ServiceDays] = None
    tariff_result: Optional[TariffResult] = None
    messages: List[ServiceMessage] = field(default_factory=list)
    subscription: str = "N"
    checksum: Optional[str] = None
    checksum_dti: Optional[str] = None
    ctx_recon: Optional[str] = None
    rec_state: str = "U"


@dataclass
class CommonData:
    """Common data shared across trip results"""
    locations: Dict[int, Location] = field(default_factory=dict)
    products: Dict[int, Product] = field(default_factory=dict)
    polylines: Dict[int, Polyline] = field(default_factory=dict)
    operators: List[Operator] = field(default_factory=list)
    remarks: List[ServiceMessage] = field(default_factory=list)
    him_messages: Dict[str, ServiceMessage] = field(default_factory=dict)
    icons: List[Icon] = field(default_factory=list)
    directions: List[Dict[str, str]] = field(default_factory=list)
    draw_styles: List[DrawStyle] = field(default_factory=list)
    layers: List[Dict[str, Any]] = field(default_factory=list)
    coordinate_systems: List[Dict[str, Any]] = field(default_factory=list)
    walking_polylines: Dict[str, Polyline] = field(default_factory=dict)  # Cache for walking polylines


# ============================================================================
# MAIN API CLASS
# ============================================================================

class RejseplanenAPI:
    """
    Complete API wrapper for Rejseplanen (Danish Journey Planner)
    
    This class provides comprehensive access to all Rejseplanen API features,
    including Plustur/Flextur (dial-a-ride) services.
    """
    
    def __init__(self, debug: bool = False, language: str = "dan", auto_fetch_walking: bool = True):
        """
        Initialize the API client
        
        Args:
            debug: Enable debug output
            language: Language code (dan, eng, deu)
            auto_fetch_walking: Automatically fetch walking polylines when planning trips
        """
        self.base_url = "https://rejseplanen.dk/bin/iphone.exe"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'Origin': 'https://rejseplanen.dk'
        }
        self.auth = {
            "type": "AID",
            "aid": "j1sa92pcj72ksh0-web"
        }
        self.client = {
            "id": "DK",
            "type": "WEB",
            "name": "rejseplanwebapp",
            "l": "vs_webapp",
            "v": "1.0.5"
        }
        self.api_version = "1.24"
        self.language = language
        self.extension = "DK.11"
        self.debug = debug
        self.auto_fetch_walking = auto_fetch_walking
        self._request_counter = 0
    
    def _create_request(self, service_requests: List[Dict]) -> Dict:
        """Create request payload with common parameters"""
        self._request_counter += 1
        return {
            "id": f"req_{int(datetime.now().timestamp()*1000)}_{self._request_counter}",
            "ver": self.api_version,
            "lang": self.language,
            "auth": self.auth,
            "client": self.client,
            "formatted": False,
            "ext": self.extension,
            "svcReqL": service_requests
        }
    
    def _make_request(self, payload: Dict) -> Optional[Dict]:
        """Make HTTP request to the API"""
        try:
            if self.debug:
                print(f"Request to: {self.base_url}")
                print(f"Services: {[s.get('meth') for s in payload.get('svcReqL', [])]}")
            
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if self.debug:
                print(f"Response status: {data.get('err', 'Unknown')}")
                if 'svcResL' in data:
                    for svc in data['svcResL']:
                        print(f"  {svc.get('meth')}: {svc.get('err')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"HTTP request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"JSON decode failed: {e}")
            return None
    
    def search_location(self, 
                       query: str,
                       location_type: LocationType = LocationType.ALL,
                       max_results: int = 10,
                       search_radius: int = 1000,
                       coordinates: Optional[Tuple[float, float]] = None) -> List[Location]:
        """
        Search for locations by name or coordinates
        
        Args:
            query: Search string
            location_type: Type of location to search
            max_results: Maximum number of results
            search_radius: Search radius in meters
            coordinates: Optional center coordinates (lat, lon)
            
        Returns:
            List of Location objects
        """
        loc_dict = {
            "name": query,
            "type": location_type.value,
            "dist": search_radius
        }
        
        if coordinates:
            loc_dict["crd"] = {
                "x": int(coordinates[1] * 1e6),
                "y": int(coordinates[0] * 1e6)
            }
        
        service_request = {
            "req": {
                "input": {
                    "field": "S",
                    "loc": loc_dict,
                    "maxLoc": max_results
                }
            },
            "meth": "LocMatch",
            "id": "1|1|"
        }
        
        payload = self._create_request([service_request])
        response = self._make_request(payload)
        
        if not response or 'svcResL' not in response:
            return []
        
        locations = []
        for svc in response['svcResL']:
            if svc.get('meth') == 'LocMatch' and 'res' in svc:
                if 'match' in svc['res'] and 'locL' in svc['res']['match']:
                    for loc_data in svc['res']['match']['locL']:
                        locations.append(Location.from_api(loc_data))
        
        return locations
    
    def plan_trip(self,
                 origin: Union[str, Location],
                 destination: Union[str, Location],
                 departure_time: Optional[datetime] = None,
                 arrival_time: Optional[datetime] = None,
                 via_stops: Optional[List[Union[str, Location]]] = None,
                 products: int = ProductClass.ALL,
                 max_changes: int = 1000,
                 min_change_time: int = -1,
                 walk_speed: int = 100,
                 max_walk_distance: int = 2000,
                 bike_carriage: bool = False,
                 transport_modes: Optional[List[TransportRequestType]] = None,
                 get_polylines: bool = True,
                 get_passlist: bool = True,
                 get_tariff: bool = True,
                 num_trips: Optional[int] = None) -> Tuple[List[Trip], CommonData, Dict[str, Any]]:
        """
        Plan trips between locations with full options
        
        Returns:
            Tuple of (trips list, common data, full response dict)
        """
        # Convert string locations to Location objects
        if isinstance(origin, str):
            origin_locs = self.search_location(origin)
            if not origin_locs:
                return [], CommonData(), {}
            origin = origin_locs[0]
        
        if isinstance(destination, str):
            dest_locs = self.search_location(destination)
            if not dest_locs:
                return [], CommonData(), {}
            destination = dest_locs[0]
        
        # Prepare time parameters
        if departure_time is None and arrival_time is None:
            departure_time = datetime.now()
        
        if arrival_time:
            out_frwd = False
            time_obj = arrival_time
        else:
            out_frwd = True
            time_obj = departure_time
        
        out_time = time_obj.strftime("%H%M%S")
        out_date = time_obj.strftime("%Y%m%d")
        
        # Build location dictionaries
        dep_loc = self._build_location_dict(origin)
        arr_loc = self._build_location_dict(destination)
        
        # Default transport modes
        if not transport_modes:
            transport_modes = [TransportRequestType.WALK_PUBLIC]
        
        # Build filters
        jny_filters = []
        for mode in transport_modes:
            jny_filters.append({
                "type": "GROUP",
                "mode": "INC",
                "value": mode.value
            })
        jny_filters.append({
            "type": "PROD",
            "mode": "INC",
            "value": products
        })
        
        # GIS filters for walking/cycling
        gis_filters = [[
            {"type": "P", "mode": "F", "profile": {
                "type": "F", "maxdist": str(max_walk_distance),
                "speed": str(walk_speed), "enabled": True}},
            {"type": "P", "mode": "F", "profile": {
                "type": "B", "maxdist": str(max_walk_distance),
                "speed": str(walk_speed), "enabled": bike_carriage}},
            {"type": "P", "mode": "B", "profile": {
                "type": "F", "maxdist": str(max_walk_distance),
                "speed": str(walk_speed), "enabled": True}},
            {"type": "P", "mode": "B", "profile": {
                "type": "B", "maxdist": str(max_walk_distance),
                "speed": str(walk_speed), "enabled": bike_carriage}},
            {"type": "P", "mode": "T", "profile": {
                "type": "F", "speed": str(walk_speed)}}
        ]]
        
        # Build request
        service_request = {
            "meth": "TripSearch",
            "req": {
                "getConGroups": True,
                "jnyFltrL": jny_filters,
                "getPolyline": get_polylines,
                "getPasslist": get_passlist,
                "depLocL": [dep_loc],
                "arrLocL": [arr_loc],
                "outFrwd": out_frwd,
                "outTime": out_time,
                "outDate": out_date,
                "liveSearch": False,
                "maxChg": str(max_changes),
                "minChgTime": str(min_change_time),
                "gisFltrL": gis_filters,
                "getIV": True,
                "getTariff": get_tariff
            },
            "id": "1|1|"
        }
        
        # Add via stops
        if via_stops:
            via_locs = []
            for via in via_stops:
                if isinstance(via, str):
                    via_search = self.search_location(via)
                    if via_search:
                        via_locs.append(self._build_location_dict(via_search[0]))
                else:
                    via_locs.append(self._build_location_dict(via))
            if via_locs:
                service_request["req"]["viaLocL"] = via_locs
        
        # Add number of trips
        if num_trips:
            service_request["req"]["numF"] = num_trips
        
        payload = self._create_request([service_request])
        response = self._make_request(payload)
        
        if not response or 'svcResL' not in response:
            return [], CommonData(), {}
        
        trips = []
        common_data = CommonData()
        full_response = {}
        
        for svc in response['svcResL']:
            if svc.get('meth') == 'TripSearch' and 'res' in svc:
                res = svc['res']
                full_response = res
                
                # Parse common data
                if 'common' in res:
                    common_data = self._parse_common_data(res['common'])
                
                # Parse trips
                for conn in res.get('outConL', []):
                    trip = self._parse_trip(conn, common_data)
                    if trip:
                        trips.append(trip)
                        
                        # Auto-fetch walking polylines if enabled
                        if self.auto_fetch_walking and get_polylines:
                            for section in trip.sections:
                                if section.type == TransportMode.WALK and section.gis and section.gis.ctx:
                                    # Check if we already have this walking route
                                    if section.gis.ctx not in common_data.walking_polylines:
                                        coords, segments, polyline = self.get_walking_details(section.gis.ctx)
                                        if polyline:
                                            # Store in cache
                                            common_data.walking_polylines[section.gis.ctx] = polyline
                                            section.gis.polyline = polyline
                                            section.gis.segments = segments
                                    else:
                                        # Use cached polyline
                                        section.gis.polyline = common_data.walking_polylines[section.gis.ctx]
                
                # Store additional response data
                full_response['outConGrpL'] = res.get('outConGrpL', [])
                full_response['fpB'] = res.get('fpB')
                full_response['fpE'] = res.get('fpE')
                full_response['outCtxScrB'] = res.get('outCtxScrB')
                full_response['outCtxScrF'] = res.get('outCtxScrF')
                full_response['planrtTS'] = res.get('planrtTS')
        
        return trips, common_data, full_response
    
    def get_trip_details(self, ctx_recon: str) -> Optional[Trip]:
        """
        Get detailed information for a specific trip using reconstruction context
        """
        service_request = {
            "meth": "Reconstruction",
            "req": {
                "ctxRecon": ctx_recon,
                "getPolyline": True,
                "getPasslist": True,
                "getTariff": True
            },
            "id": "1|1|"
        }
        
        payload = self._create_request([service_request])
        response = self._make_request(payload)
        
        if not response or 'svcResL' not in response:
            return None
        
        for svc in response['svcResL']:
            if svc.get('meth') == 'Reconstruction' and 'res' in svc:
                res = svc['res']
                if 'common' in res and 'outConL' in res and res['outConL']:
                    common_data = self._parse_common_data(res['common'])
                    return self._parse_trip(res['outConL'][0], common_data)
        
        return None
    
    def get_walking_details(self, gis_ctx: str) -> Tuple[List[Coordinate], List[WalkingSegment], Optional[Polyline]]:
        """
        Get detailed walking route with turn-by-turn navigation
        
        Returns:
            Tuple of (coordinates, walking segments, polyline)
        """
        service_request = {
            "meth": "GisRoute",
            "req": {
                "gisCtx": gis_ctx,
                "getDescription": True,
                "getPolyline": True
            }
        }
        
        payload = self._create_request([service_request])
        response = self._make_request(payload)
        
        if not response or 'svcResL' not in response:
            return [], [], None
        
        coordinates = []
        segments = []
        polyline = None
        
        for svc in response['svcResL']:
            if svc.get('meth') == 'GisRoute' and 'res' in svc:
                res = svc['res']
                
                # Extract polylines
                if 'common' in res and 'polyL' in res['common']:
                    for poly_data in res['common']['polyL']:
                        if 'crdEncYX' in poly_data:
                            coords = self.decode_polyline(poly_data['crdEncYX'])
                            coordinates.extend([Coordinate(lat, lon) for lat, lon in coords])
                            polyline = Polyline(
                                encoded=poly_data['crdEncYX'],
                                coordinates=[Coordinate(lat, lon) for lat, lon in coords],
                                location_refs=poly_data.get('ppLocRefL', []),
                                draw_style_index=poly_data.get('lDrawStyleX'),
                                delta=poly_data.get('delta', True),
                                dimension=poly_data.get('dim', 2),
                                encoding_start=poly_data.get('crdEncS'),
                                encoding_format=poly_data.get('crdEncF')
                            )
                
                # Extract walking segments
                if 'conL' in res:
                    for con in res['conL']:
                        for sec in con.get('secL', []):
                            if 'gis' in sec and 'segL' in sec['gis']:
                                for seg_data in sec['gis']['segL']:
                                    segments.append(WalkingSegment.from_api(seg_data))
        
        return coordinates, segments, polyline
    
    def get_service_messages(self, location_ids: Optional[List[str]] = None, him_ids: Optional[List[str]] = None) -> List[ServiceMessage]:
        """Get current service messages and disruptions"""
        req_dict = {}
        
        if location_ids:
            req_dict["locL"] = [{"lid": lid} for lid in location_ids]
        
        if him_ids:
            req_dict["himIdL"] = him_ids
        
        service_request = {
            "meth": "HimSearch",
            "req": req_dict,
            "id": "1|1|"
        }
        
        payload = self._create_request([service_request])
        response = self._make_request(payload)
        
        if not response or 'svcResL' not in response:
            return []
        
        messages = []
        for svc in response['svcResL']:
            if svc.get('meth') == 'HimSearch' and 'res' in svc:
                if 'msgL' in svc['res']:
                    for msg_data in svc['res']['msgL']:
                        messages.append(ServiceMessage.from_api(msg_data))
        
        return messages
    
    def scroll_trips(self, context: str, direction: str = "F", num_trips: int = 3) -> Tuple[List[Trip], CommonData]:
        """Scroll/paginate through trip results"""
        service_request = {
            "meth": "TripSearch",
            "req": {
                "ctxScr": context,
                "numF": num_trips if direction == "F" else None,
                "numB": num_trips if direction == "B" else None
            },
            "id": "1|1|"
        }
        
        payload = self._create_request([service_request])
        response = self._make_request(payload)
        
        if not response or 'svcResL' not in response:
            return [], CommonData()
        
        trips = []
        common_data = CommonData()
        
        for svc in response['svcResL']:
            if svc.get('meth') == 'TripSearch' and 'res' in svc:
                res = svc['res']
                
                if 'common' in res:
                    common_data = self._parse_common_data(res['common'])
                
                for conn in res.get('outConL', []):
                    trip = self._parse_trip(conn, common_data)
                    if trip:
                        trips.append(trip)
        
        return trips, common_data
    
    def decode_polyline(self, encoded: str) -> List[Tuple[float, float]]:
        """
        Decode Rejseplanen's delta-encoded polyline format
        
        Returns:
            List of (latitude, longitude) tuples in decimal degrees
        """
        if not encoded:
            return []
        
        coordinates = []
        index = 0
        lat = 0
        lon = 0
        
        while index < len(encoded):
            # Decode latitude delta
            shift = 0
            result = 0
            while index < len(encoded):
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            lat_delta = (~(result >> 1)) if (result & 1) else (result >> 1)
            lat += lat_delta
            
            if index >= len(encoded):
                break
            
            # Decode longitude delta
            shift = 0
            result = 0
            while index < len(encoded):
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            lon_delta = (~(result >> 1)) if (result & 1) else (result >> 1)
            lon += lon_delta
            
            # Convert to decimal degrees
            coordinates.append((lat / 1e5, lon / 1e5))
        
        return coordinates
    
    def _build_location_dict(self, location: Location) -> Dict:
        """Build location dictionary for API request"""
        return {
            "lid": location.lid,
            "type": location.type,
            "name": location.name,
            "icoX": location.icon_index or 0,
            "extId": location.ext_id or "",
            "state": location.state,
            "crd": {
                "x": int(location.coordinate.lon * 1e6),
                "y": int(location.coordinate.lat * 1e6),
                "layerX": location.coordinate.layer_index,
                "crdSysX": location.coordinate.crd_sys_index
            },
            "pCls": location.product_classes,
            "pRefL": location.product_refs,
            "wt": location.weight,
            "isMainMast": location.is_main_mast
        }
    
    def _parse_common_data(self, common: Dict) -> CommonData:
        """Parse common data section"""
        data = CommonData()
        
        # Parse locations
        if 'locL' in common:
            for i, loc_data in enumerate(common['locL']):
                data.locations[i] = Location.from_api(loc_data)
        
        # Parse products
        if 'prodL' in common:
            for i, prod_data in enumerate(common['prodL']):
                data.products[i] = Product.from_api(prod_data)
        
        # Parse and decode polylines
        if 'polyL' in common:
            for i, poly_data in enumerate(common['polyL']):
                if 'crdEncYX' in poly_data:
                    coords = self.decode_polyline(poly_data['crdEncYX'])
                    data.polylines[i] = Polyline(
                        encoded=poly_data['crdEncYX'],
                        coordinates=[Coordinate(lat, lon) for lat, lon in coords],
                        location_refs=poly_data.get('ppLocRefL', []),
                        draw_style_index=poly_data.get('lDrawStyleX'),
                        delta=poly_data.get('delta', True),
                        dimension=poly_data.get('dim', 2),
                        encoding_start=poly_data.get('crdEncS'),
                        encoding_format=poly_data.get('crdEncF')
                    )
        
        # Parse operators
        if 'opL' in common:
            for op_data in common['opL']:
                data.operators.append(Operator(
                    name=op_data.get('name', ''),
                    icon_index=op_data.get('icoX')
                ))
        
        # Parse remarks/messages
        if 'remL' in common:
            for rem_data in common['remL']:
                data.remarks.append(ServiceMessage.from_api(rem_data))
        
        # Parse icons
        if 'icoL' in common:
            for ico_data in common['icoL']:
                data.icons.append(Icon.from_api(ico_data))
        
        # Parse directions
        if 'dirL' in common:
            data.directions = common['dirL']
        
        # Parse draw styles
        if 'lDrawStyleL' in common:
            for style_data in common['lDrawStyleL']:
                data.draw_styles.append(DrawStyle.from_api(style_data))
        
        # Parse layers and coordinate systems
        data.layers = common.get('layerL', [])
        data.coordinate_systems = common.get('crdSysL', [])
        
        return data
    
    def _parse_trip(self, conn: Dict, common_data: CommonData) -> Optional[Trip]:
        """Parse a single trip/connection"""
        try:
            sections = []
            
            # Parse sections
            for sec_data in conn.get('secL', []):
                section = TripSection(
                    type=TransportMode(sec_data['type']),
                    departure=sec_data.get('dep'),
                    arrival=sec_data.get('arr')
                )
                
                # Check for call-ahead service flag (Plustur)
                if section.departure and 'dCaS' in section.departure:
                    section.call_ahead_service = section.departure['dCaS']
                    section.booking_required = True
                    section.booking_deadline_minutes = 120  # Default 2 hours for Plustur
                
                # Handle walking sections
                if section.type == TransportMode.WALK and 'gis' in sec_data:
                    gis_data = sec_data['gis']
                    section.gis = GisInfo(
                        distance=gis_data.get('dist', 0),
                        duration_seconds=gis_data.get('durS', ''),
                        ctx=gis_data.get('ctx', ''),
                        provider=gis_data.get('gisPrvr', 'E')
                    )
                
                # Handle TETA (Plustur/dial-a-ride) sections
                elif section.type == TransportMode.TETA and 'jny' in sec_data:
                    jny_data = sec_data['jny']
                    section.journey = Journey(
                        jid=jny_data.get('jid', ''),
                        date=jny_data.get('date', ''),
                        product_index=jny_data.get('prodX'),
                        direction_text=jny_data.get('dirTxt'),
                        direction_flag=jny_data.get('dirFlg'),
                        status=jny_data.get('status'),
                        is_reachable=jny_data.get('isRchbl', True),
                        subscription=jny_data.get('subscr', 'N'),
                        ctx_recon=jny_data.get('ctxRecon')
                    )
                    
                    # Get polyline indices for Plustur route
                    if 'polyG' in jny_data and 'polyXL' in jny_data['polyG']:
                        section.journey.polyline_indices = jny_data['polyG']['polyXL']
                    
                    # Parse journey messages
                    if 'msgL' in jny_data:
                        for msg_data in jny_data['msgL']:
                            section.journey.messages.append(ServiceMessage.from_api(msg_data))
                
                # Handle journey sections (train/bus/metro)
                elif section.type == TransportMode.JNY and 'jny' in sec_data:
                    jny_data = sec_data['jny']
                    section.journey = Journey(
                        jid=jny_data.get('jid', ''),
                        date=jny_data.get('date', ''),
                        product_index=jny_data.get('prodX'),
                        direction_text=jny_data.get('dirTxt'),
                        direction_flag=jny_data.get('dirFlg'),
                        status=jny_data.get('status'),
                        is_reachable=jny_data.get('isRchbl', True),
                        subscription=jny_data.get('subscr', 'N'),
                        ctx_recon=jny_data.get('ctxRecon')
                    )
                    
                    # Parse stops
                    if 'stopL' in jny_data:
                        for stop_data in jny_data['stopL']:
                            section.journey.stops.append(Stop.from_api(stop_data))
                    
                    # Get polyline indices
                    if 'polyG' in jny_data and 'polyXL' in jny_data['polyG']:
                        section.journey.polyline_indices = jny_data['polyG']['polyXL']
                    
                    # Parse journey messages
                    if 'msgL' in jny_data:
                        for msg_data in jny_data['msgL']:
                            section.journey.messages.append(ServiceMessage.from_api(msg_data))
                
                # Parse section messages
                if 'msgL' in sec_data:
                    for msg_data in sec_data['msgL']:
                        section.messages.append(ServiceMessage.from_api(msg_data))
                
                sections.append(section)
            
            # Parse service days
            service_days = None
            if 'sDays' in conn:
                service_days = ServiceDays.from_api(conn['sDays'])
            
            # Parse tariff result
            tariff_result = None
            if 'trfRes' in conn:
                trf = conn['trfRes']
                tariff_result = TariffResult(
                    status_code=trf.get('statusCode', ''),
                    fare_sets=[],  # Would need to parse fareSetL
                    external_content=trf.get('extCont'),
                    messages=trf.get('msgL', [])
                )
            
            # Parse trip messages
            messages = []
            if 'msgL' in conn:
                for msg_data in conn['msgL']:
                    messages.append(ServiceMessage.from_api(msg_data))
            
            return Trip(
                id=conn.get('cid', ''),
                date=conn.get('date', ''),
                duration=conn.get('dur', ''),
                changes=conn.get('chg', 0),
                departure_time=conn.get('dep', {}).get('dTimeS', ''),
                arrival_time=conn.get('arr', {}).get('aTimeS', ''),
                sections=sections,
                service_days=service_days,
                tariff_result=tariff_result,
                messages=messages,
                subscription=conn.get('conSubscr', 'N'),
                checksum=conn.get('cksum'),
                checksum_dti=conn.get('cksumDti'),
                ctx_recon=conn.get('ctxRecon'),
                rec_state=conn.get('recState', 'U')
            )
            
        except Exception as e:
            if self.debug:
                print(f"Error parsing trip: {e}")
            return None
    
    def print_trip_details(self, trip: Trip, common_data: CommonData):
        """Print detailed trip information"""
        print(f"\n{'='*70}")
        print(f"Trip ID: {trip.id}")
        print(f"Date: {trip.date}")
        print(f"Duration: {trip.duration[:2]}:{trip.duration[2:4]}:{trip.duration[4:6]}")
        print(f"Changes: {trip.changes}")
        print(f"Departure: {trip.departure_time[:2]}:{trip.departure_time[2:4]}")
        print(f"Arrival: {trip.arrival_time[:2]}:{trip.arrival_time[2:4]}")
        
        if trip.service_days:
            print(f"Service Days: {trip.service_days.regular}")
            if trip.service_days.irregular:
                print(f"  Also: {trip.service_days.irregular}")
        
        print(f"\nSections:")
        for i, section in enumerate(trip.sections, 1):
            print(f"\n  {i}. {section.type.value}")
            
            # Special handling for Plustur
            if section.type == TransportMode.TETA:
                print(f"     ⚠️ PLUSTUR - Dial-a-ride service")
                if section.call_ahead_service:
                    print(f"     📞 Booking required: Min. 2 hours before departure")
                    print(f"     ⏰ Times are approximate - exact times given when booking")
            
            # Get location names
            if section.departure and 'locX' in section.departure:
                loc = common_data.locations.get(section.departure['locX'])
                if loc:
                    print(f"     From: {loc.name}")
                    if section.departure.get('dTimeS'):
                        time = section.departure['dTimeS']
                        print(f"     Departure: {time[:2]}:{time[2:4]}")
            
            if section.arrival and 'locX' in section.arrival:
                loc = common_data.locations.get(section.arrival['locX'])
                if loc:
                    print(f"     To: {loc.name}")
                    if section.arrival.get('aTimeS'):
                        time = section.arrival['aTimeS']
                        print(f"     Arrival: {time[:2]}:{time[2:4]}")
            
            if section.gis:
                print(f"     Distance: {section.gis.distance}m")
                print(f"     Duration: {section.gis.duration_seconds}")
                if section.gis.polyline:
                    print(f"     GPS points: {len(section.gis.polyline.coordinates)}")
            
            if section.journey:
                if section.journey.product_index is not None:
                    prod = common_data.products.get(section.journey.product_index)
                    if prod:
                        print(f"     Line: {prod.name}")
                        if prod.category_out:
                            print(f"     Category: {prod.category_out.strip()}")
                
                if section.journey.direction_text:
                    print(f"     Direction: {section.journey.direction_text}")
                
                if section.journey.polyline_indices:
                    total_points = sum(len(common_data.polylines[idx].coordinates) 
                                     for idx in section.journey.polyline_indices 
                                     if idx in common_data.polylines)
                    if total_points > 0:
                        print(f"     GPS points: {total_points}")
        
        if trip.tariff_result and trip.tariff_result.external_content:
            print(f"\nFare Info: {trip.tariff_result.external_content.get('text', 'Available')}")
        
        for msg in trip.messages:
            if msg.text:
                if msg.code == 'teletaxi':
                    print(f"\n📞 {msg.text}")
                else:
                    print(f"\n⚠ {msg.text}")
