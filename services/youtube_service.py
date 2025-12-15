
import re
from datetime import datetime, timezone
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def parse_duration(duration_str):
    """
    ISO 8601 duration 문자열(PT1H2M10S)을 초 단위로 변환합니다.
    """
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration_str)
    if not match:
        return 0
    
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    
    return hours * 3600 + minutes * 60 + seconds

def calculate_popularity_score(video_info):
    """
    Time Decay (Hacker News style) 알고리즘을 사용하여 인기 점수를 계산합니다.
    Score = (V*1 + L*30 + C*100) / (Time + 2)^1.8
    """
    view_count = video_info['Views']
    like_count = video_info['Likes'] if video_info['Likes'] else 0
    # 댓글 수는 API 비용 문제로 생략하거나 0으로 처리 (현재 로직상 데이터가 없음)
    comment_count = 0 
    
    # 가중치
    W_VIEW = 1
    W_LIKE = 30
    W_COMMENT = 100
    GRAVITY = 1.8
    
    base_score = (view_count * W_VIEW) + (like_count * W_LIKE) + (comment_count * W_COMMENT)
    
    # 시간 감쇠 적용
    # 게시 시간 파싱 (YYYY-MM-DD or ISO 8601)
    # search_youtube_videos에서 'Date'는 'YYYY-MM-DD'로 잘려있을 수 있음.
    # 정확도를 위해 원본 datetime 객체를 사용하거나 여기서 다시 파싱.
    # 현재 `search_youtube_videos`에서 `publishedAt` 전체를 넘겨주도록 수정 필요.
    # 일단 'Date'가 YYYY-MM-DD만 있다고 가정하고 00:00:00으로 처리
    try:
        pub_date = datetime.strptime(video_info['Date'], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except:
        # 실패 시 현재 시간으로 간주 (감쇠 없음)
        pub_date = datetime.now(timezone.utc)

    time_diff = datetime.now(timezone.utc) - pub_date
    hours_age = time_diff.total_seconds() / 3600
    
    trend_score = base_score / pow((hours_age + 2), GRAVITY)
    return trend_score

def search_youtube_videos(api_key, query, max_results=50, region_code='KR', published_after=None, sort_by='trend'):
    """
    키워드로 유튜브 영상을 검색하고 롱폼/숏폼으로 분류하여 반환합니다.
    sort_by: 'trend' (화제성 점수순) or 'viewCount' (조회수순)
    """
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # 1. 검색 (Video ID 확보)
        search_response = youtube.search().list(
            q=query,
            type='video',
            part='id',
            maxResults=max_results,
            regionCode=region_code,
            publishedAfter=published_after,
            order='viewCount' # 기본적으로 조회수 순으로 검색 (API 지원 시)
        ).execute()
        
        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        
        if not video_ids:
            return [], []
            
        # 2. 상세 정보 조회 (통계, 길이 등)
        videos_response = youtube.videos().list(
            id=','.join(video_ids),
            part='snippet,statistics,contentDetails'
        ).execute()
        
        long_forms = []
        shorts = []
        
        for item in videos_response.get('items', []):
            snippet = item['snippet']
            stats = item.get('statistics', {})
            content_details = item.get('contentDetails', {})
            
            title = snippet['title']
            published_at = snippet['publishedAt'][:10] # YYYY-MM-DD
            
            # 통계 (None 처리)
            view_count = int(stats.get('viewCount', 0))
            like_count = int(stats.get('likeCount', 0)) if 'likeCount' in stats else 0
            
            # 길이 파싱
            duration_str = content_details.get('duration', 'PT0S')
            duration_sec = parse_duration(duration_str)
            
            # 썸네일
            thumbnail = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
            
            video_info = {
                'Thumbnail': thumbnail,
                'Title': title,
                'Views': view_count,
                'Likes': like_count,
                'Date': published_at,
                'Link': f"https://www.youtube.com/watch?v={item['id']}",
                'Score': 0 # 초기값
            }
            
            # 점수 계산 (Raw Score)
            video_info['Score'] = calculate_popularity_score(video_info)
            
            # 60초 이하는 숏폼으로 분류
            if duration_sec <= 60:
                shorts.append(video_info)
            else:
                long_forms.append(video_info)
        
        # 스케일링 (0~100점) 및 정렬
        for video_list in [long_forms, shorts]:
            if not video_list:
                continue
                
            # 최대 점수 찾기
            max_score = max(v['Score'] for v in video_list)
            
            # 정규화
            for v in video_list:
                if max_score > 0:
                    v['Score'] = round((v['Score'] / max_score) * 100, 1)
                else:
                    v['Score'] = 0

            # 정렬
            if sort_by == 'trend':
                video_list.sort(key=lambda x: x['Score'], reverse=True)
            else: # viewCount
                video_list.sort(key=lambda x: x['Views'], reverse=True)
                
        return long_forms, shorts

    except HttpError as e:
        st.error(f"YouTube API 오류 발생: {e}")
        return [], []
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return [], []

def get_youtube_trending_tags(api_key, region_code='KR', max_results=50):
    """
    YouTube Data API를 사용하여 인기 동영상의 태그를 수집합니다.
    """
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # 인기 동영상 리스트 가져오기
        request = youtube.videos().list(
            part="snippet",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results
        )
        response = request.execute()
        
        all_tags = []
        video_data = []

        for item in response.get('items', []):
            snippet = item['snippet']
            title = snippet['title']
            tags = snippet.get('tags', [])
            video_id = item['id']
            
            # 태그 수집
            all_tags.extend(tags)
            
            video_data.append({
                'Title': title,
                'Tags': ", ".join(tags) if tags else "None",
                'Link': f"https://www.youtube.com/watch?v={video_id}"
            })
            
        return all_tags, video_data
        
    except HttpError as e:
        st.error(f"YouTube API 오류 발생: {e}")
        return [], []
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return [], []
