import os
from datetime import datetime

def parse_nvr_filename(filename):
    """
    Парсит специфическое имя файла NVR:
    Camera_01_10.12.0.35_10.12.0.235_20260401113050_20260401113550_3084159.mp4
    """
    # Убираем расширение
    base_name = os.path.splitext(filename)[0]
    parts = base_name.split('_')
    
    metadata = {
        "camera_id": "unknown",
        "camera_ip": None,
        "nvr_ip": None,
        "start_time": None,
        "end_time": None,
        "session_id": None
    }
    
    try:
        if len(parts) >= 7:
            # 1. Camera_01
            metadata["camera_id"] = f"{parts[0]}_{parts[1]}"
            # 2. IPs
            metadata["camera_ip"] = parts[2]
            metadata["nvr_ip"] = parts[3]
            
            # 3. Timestamps (20260401113050)
            def format_ts(ts_str):
                try:
                    dt = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    return ts_str
            
            metadata["start_time"] = format_ts(parts[4])
            metadata["end_time"] = format_ts(parts[5])
            metadata["session_id"] = parts[6]
        else:
            # Fallback для коротких имен
            metadata["camera_id"] = parts[0]
            
    except Exception as e:
        print(f"Ошибка парсинга имени файла {filename}: {e}")
        
    return metadata


def extract_camera_id(source_path):
    """Извлекает camera_id из пути к файлу."""
    if not source_path:
        return "unknown"
    filename = os.path.basename(source_path)
    return parse_nvr_filename(filename).get("camera_id", "unknown")
