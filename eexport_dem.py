import ee
import os
import time

# 여기에 1단계에서 생성한 본인의 Google Cloud 프로젝트 ID를 입력하세요.
GCP_PROJECT_ID = 'triple-virtue-457623-v3' 
try:
    # 프로젝트 ID를 명시적으로 지정하여 초기화합니다.
    # gcloud 인증을 마쳤다면 이 과정이 원활하게 진행됩니다.
    ee.Initialize(project=GCP_PROJECT_ID)
    print(f"Google Earth Engine 인증 성공! (Project: {GCP_PROJECT_ID})")
except Exception as e:
    print(f"인증에 실패했습니다. gcloud CLI 설정 및 프로젝트 ID를 확인해주세요.\n에러: {e}")
    exit()

# 1. DEM을 추출할 지역(AOI) 설정
latitude = 37.5665
longitude = 126.9780
buffer_radius_meters = 2000
region_name = 'seoul_city_hall'

aoi = ee.Geometry.Point(longitude, latitude).buffer(buffer_radius_meters)
print(f"'{region_name}' 지역의 DEM 데이터를 요청합니다.")

# 2. DEM 데이터 불러오기 및 자르기
dem_image = ee.Image('USGS/SRTMGL1_003').select('elevation')
clipped_dem = dem_image.clip(aoi)

# 3. 로컬 파일로 직접 다운로드 (geemap 활용)
# geemap 라이브러리가 설치되어 있어야 합니다 (pip install geemap)
import geemap

output_directory = 'DEM_data'
output_filename = os.path.join(output_directory, f'{region_name}_dem.tif')

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

print(f"\n파일 다운로드를 시작합니다...\n저장 경로: {output_filename}")

geemap.ee_export_image(
    clipped_dem,
    filename=output_filename,
    scale=30,
    region=aoi.bounds(),
    file_per_band=False
)

while not os.path.exists(output_filename):
    print("다운로드 진행 중...")
    time.sleep(5)

print(f"\n🎉 다운로드 완료! '{output_filename}' 파일을 확인해 주세요.")