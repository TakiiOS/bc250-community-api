import uvicorn
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import datetime

app = FastAPI(
    title="AMD BC-250 Community Settings API",
    description="Backend Service for sharing & querying game compatibility and 1-click settings for AMD BC-250 (6CU & 8CU variants)",
    version="1.0.0"
)

class CUVariantEnum(str, Enum):
    CU_6 = "6CU"
    CU_8 = "8CU"

class SystemSettings(BaseModel):
    tdp_limit_watts: int = Field(..., example=35, description="Target TDP limit in Watts")
    cpu_cores_enabled: int = Field(8, example=8, description="Active CPU cores")
    smt_enabled: bool = True
    gpu_clock_mhz: Optional[int] = None

class ConfigFilePayload(BaseModel):
    relative_path: str = Field(..., example="~/.local/share/Steam/steamapps/compatdata/1091500/pfx/drive_c/users/steamuser/AppData/Local/CD Projekt Red/Cyberpunk 2077/UserSettings.json")
    file_type: str = Field("json", example="json")
    settings_payload: Dict[str, Any]

class GameConfigCreate(BaseModel):
    appid: int = Field(..., example=1091500)
    game_title: str = Field(..., example="Cyberpunk 2077")
    cu_variant: CUVariantEnum = Field(..., description="Target hardware revision (6CU or 8CU)")
    author: str = Field("Anonymous", example="BC250_Master")
    target_fps: int = Field(60, example=60)
    reported_avg_fps: int = Field(58, example=58)
    proton_version: str = Field("GE-Proton8-32", example="GE-Proton8-32")
    in_game_preset: str = Field("Medium", example="Medium-Custom FSR 2.1")
    description: str = Field("", example="60FPS locked for 8CU Custom Bios")
    system_settings: SystemSettings
    config_files: List[ConfigFilePayload] = []

class GameConfigResponse(GameConfigCreate):
    id: str
    rating_votes: int = 1
    created_at: str

# In-Memory Database (Replace with PostgreSQL / Supabase in production)
DB_CONFIGS: List[Dict[str, Any]] = [
    {
        "id": "cfg-bc250-8cu-cp2077",
        "appid": 1091500,
        "game_title": "Cyberpunk 2077",
        "cu_variant": "8CU",
        "author": "BC250_Overclock",
        "target_fps": 60,
        "reported_avg_fps": 59,
        "proton_version": "GE-Proton8-32",
        "in_game_preset": "Medium FSR Quality",
        "description": "Requires 8CU Custom Bios + 35W TDP limit via RyZenAdj",
        "rating_votes": 142,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "system_settings": {
            "tdp_limit_watts": 35,
            "cpu_cores_enabled": 8,
            "smt_enabled": True
        },
        "config_files": []
    },
    {
        "id": "cfg-bc250-6cu-cp2077",
        "appid": 1091500,
        "game_title": "Cyberpunk 2077",
        "cu_variant": "6CU",
        "author": "Stock_Ariel",
        "target_fps": 40,
        "reported_avg_fps": 42,
        "proton_version": "Proton Experimental",
        "in_game_preset": "Low-Medium mix",
        "description": "Optimized for stock 6CU cards at 28W TDP",
        "rating_votes": 67,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "system_settings": {
            "tdp_limit_watts": 28,
            "cpu_cores_enabled": 6,
            "smt_enabled": True
        },
        "config_files": []
    }
]

@app.get("/")
def root():
    return {"service": "AMD BC-250 Community API", "status": "online"}

@app.get("/api/v1/configs", response_model=List[GameConfigResponse])
def get_configs(
    appid: Optional[int] = Query(None, description="Filter by Steam AppID"),
    cu_variant: Optional[CUVariantEnum] = Query(None, description="Filter by 6CU or 8CU")
):
    """Retrieve community game configs filtered by AppID and CU variant (6CU vs 8CU)."""
    results = DB_CONFIGS
    if appid:
        results = [c for c in results if c["appid"] == appid]
    if cu_variant:
        results = [c for c in results if c["cu_variant"] == cu_variant.value]
    return results

@app.post("/api/v1/configs", response_model=GameConfigResponse, status_code=210)
def submit_config(payload: GameConfigCreate):
    """Allows BC-250 users to share their working game configuration for 6CU or 8CU."""
    new_id = f"cfg-{payload.cu_variant.value}-{payload.appid}-{len(DB_CONFIGS)+1}"
    new_entry = payload.dict()
    new_entry["id"] = new_id
    new_entry["rating_votes"] = 1
    new_entry["created_at"] = datetime.datetime.utcnow().isoformat()
    
    DB_CONFIGS.append(new_entry)
    return new_entry

@app.post("/api/v1/configs/{config_id}/vote")
def vote_config(config_id: str):
    """Upvote a working community configuration."""
    for cfg in DB_CONFIGS:
        if cfg["id"] == config_id:
            cfg["rating_votes"] += 1
            return {"status": "success", "new_votes": cfg["rating_votes"]}
    raise HTTPException(status_code=404, detail="Configuration not found")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
