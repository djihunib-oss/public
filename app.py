import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
from datetime import datetime, timedelta

# 사용자 정의 서비스 임포트
from services.youtube_service import get_youtube_trending_tags, search_youtube_videos
from services.naver_service import get_naver_trending_topics, get_naver_news_list, get_naver_ranking_news

# 페이지 설정 (반드시 가장 처음에 호출)
st.set_page_config(
    page_title="Trend Analyzer",
    page_icon="📊",
    layout="wide"
)

# --- Shared Utility Functions ---
def display_video_grid(video_list, num_columns=2):
    """
    비디오 리스트를 그리드(앨범) 형태로 출력합니다.
    """
    # 행 단위로 처리
    for i in range(0, len(video_list), num_columns):
        cols = st.columns(num_columns)
        # 현재 행에 들어갈 비디오들
        row_videos = video_list[i:i+num_columns]
        
        for idx, video in enumerate(row_videos):
            with cols[idx]:
                # 썸네일 (클릭 시 이동은 안되지만 시각적으로 강조)
                if video['Thumbnail']:
                    st.image(video['Thumbnail'], use_container_width=True)
                
                # 제목 (링크 포함)
                st.markdown(f"**[{video['Title']}]({video['Link']})**")
                
                # 점수 및 통계 정보
                if video['Score'] >= 80:
                    score_str = f":red[**🔥 화제성: {video['Score']}점**]"
                elif video['Score'] >= 50:
                    score_str = f":orange[**🔥 화제성: {video['Score']}점**]"
                else:
                    score_str = f"**🔥 화제성: {video['Score']}점**"
                
                st.markdown(score_str)
                st.caption(f"👁️ {video['Views']:,} | ❤️ {video['Likes']:,} | 📅 {video['Date']}")
                st.write("---")

# --- Page Functions ---

def page_trend_analysis():
    st.title("📊 트렌드 데이터 분석")
    st.markdown("YouTube 인기 동영상과 네이버 검색 트렌드를 분석합니다.")
    
    # 공통 설정
    with st.expander("분석 옵션 설정", expanded=True):
        max_results = st.slider("분석 데이터 개수", 10, 100, 50, 10)
        
    tab1, tab2 = st.tabs(["📺 YouTube 인기 동영상", "🇰🇷 네이버 검색 트렌드"])
    
    # YouTube 탭
    with tab1:
        col1, col2 = st.columns([1, 3])
        with col1:
            country_options = ['KR', 'US', 'JP', 'GB', 'IN']
            selected_country = st.selectbox("국가 선택", country_options, index=0)
            yt_btn = st.button("YouTube 분석 시작", key='yt_start')

        if yt_btn:
            api_key = st.secrets.get("YOUTUBE_API_KEY", "")
            if not api_key:
                st.error("⚠️ YouTube API Key가 설정되지 않았습니다. 'API 설정' 메뉴에서 키를 입력해주세요.")
            else:
                with st.spinner('YouTube 데이터를 불러오는 중입니다...'):
                    tags, raw_data_list = get_youtube_trending_tags(
                        api_key, 
                        region_code=selected_country, 
                        max_results=max_results
                    )
                    
                    if tags:
                        # 시각화
                        tag_counts = Counter(tags)
                        top_20_tags = tag_counts.most_common(20)
                        df_tags = pd.DataFrame(top_20_tags, columns=['Keyword', 'Frequency']).sort_values(by='Frequency', ascending=True)
                        
                        st.subheader(f"인기 태그 Top 20 ({selected_country})")
                        fig = px.bar(df_tags, x='Frequency', y='Keyword', orientation='h', text='Frequency')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 데이터 테이블
                        with st.expander("상세 데이터 보기"):
                            st.dataframe(
                                pd.DataFrame(raw_data_list),
                                use_container_width=True,
                                column_config={
                                    "Link": st.column_config.LinkColumn("Watch Video", display_text="YouTube에서 보기")
                                }
                            )
                    else:
                        st.warning("데이터를 가져올 수 없습니다.")

    # Naver 탭
    with tab2:
        col1, col2 = st.columns([1, 1])
        with col1:
            naver_category = st.selectbox("카테고리", ['뉴스', '스포츠'])
        with col2:
            naver_sort = st.radio("정렬", ('최신순', '관련도순'), horizontal=True)
        
        custom_query = st.text_input("검색어 직접 입력 (선택사항)")
        naver_btn = st.button("네이버 트렌드 분석 시작", key='naver_start')
        
        if naver_btn:
            # API Key Load
            client_id = st.secrets.get("NAVER_CLIENT_ID", "")
            client_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
            
            if not client_id or not client_secret:
                st.error("⚠️ 네이버 API 키가 설정되지 않았습니다. 'API 설정' 메뉴에서 입력해주세요.")
            else:
                # 매핑
                cat_map = {'뉴스': 'news', '스포츠': 'sports'}
                sort_map = {'최신순': 'date', '관련도순': 'sim'}
                
                with st.spinner('네이버 트렌드 분석 중...'):
                    words, articles = get_naver_trending_topics(
                        client_id, client_secret, 
                        category=cat_map[naver_category], 
                        max_results=max_results, 
                        sort=sort_map.get(naver_sort, 'date'), 
                        custom_query=custom_query
                    )
                    
                    if words:
                        # 시각화
                        word_counts = Counter(words)
                        top_20 = word_counts.most_common(20)
                        df_words = pd.DataFrame(top_20, columns=['Keyword', 'Frequency']).sort_values(by='Frequency', ascending=True)
                        
                        st.subheader(f"네이버 {naver_category} 키워드 Top 20")
                        fig = px.bar(df_words, x='Frequency', y='Keyword', orientation='h', text='Frequency', color='Frequency', color_continuous_scale='Viridis')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 데이터 테이블
                        with st.expander("수집된 기사 목록"):
                            st.dataframe(
                                pd.DataFrame(articles),
                                use_container_width=True,
                                column_config={
                                    "Link": st.column_config.LinkColumn("Read Article", display_text="기사 원문 보기")
                                }
                            )
                    else:
                        st.warning("트렌드 데이터를 찾을 수 없습니다.")

def page_youtube_analysis():
    st.title("🎥 유튜브 영상 검색 및 분석")
    st.markdown("키워드로 영상을 검색하고 **롱폼(Long-form)**과 **숏폼(Shorts)**으로 구분하여 분석합니다.")
    
    # Initialize session state
    if 'yt_long_forms' not in st.session_state:
        st.session_state['yt_long_forms'] = []
    if 'yt_shorts' not in st.session_state:
        st.session_state['yt_shorts'] = []
    if 'yt_search_done' not in st.session_state:
        st.session_state['yt_search_done'] = False
        
    # 검색 옵션 (Expandable)
    with st.expander("검색 옵션 설정", expanded=True):
        col_opt1, col_opt2, col_opt3 = st.columns(3)
        with col_opt1:
            country_options = ['KR', 'US', 'JP', 'GB', 'IN']
            yt_region = st.selectbox("국가 선택", country_options, index=0, key='yt_region_search')
        with col_opt2:
            date_range = st.selectbox("게시일 필터", ['전체', '최근 1주', '최근 1개월', '최근 1년'], index=0)
        with col_opt3:
            yt_max = st.slider("검색 개수", 50, 200, 50, 10, key='yt_max_search')

    # 정렬 옵션
    sort_option = st.radio("정렬 기준", ["🔥 화제성 순 (Trend Score)", "👁️ 조회수 순 (View Count)"], horizontal=True, key='yt_sort')
    sort_key = 'trend' if '화제성' in sort_option else 'viewCount'

    col1, col2 = st.columns([3, 1])
    with col1:
        yt_query = st.text_input("검색어 입력", placeholder="예: 아이돌 직캠, 요리 레시피")
    with col2:
        st.write("") 
        st.write("") 
        yt_search_btn = st.button("검색 시작 🔍", use_container_width=True)
        
    if yt_search_btn:
        api_key = st.secrets.get("YOUTUBE_API_KEY", "")
        if not api_key:
            st.error("⚠️ YouTube API Key가 없습니다.")
        else:
            if not yt_query:
                st.warning("경고: 검색어를 입력해주세요.")
            else:
                # 날짜 필터 로직
                published_after = None
                now = datetime.utcnow()
                if date_range == '최근 1주':
                    published_after = (now - timedelta(weeks=1)).isoformat() + 'Z'
                elif date_range == '최근 1개월':
                    published_after = (now - timedelta(days=30)).isoformat() + 'Z'
                elif date_range == '최근 1년':
                    published_after = (now - timedelta(days=365)).isoformat() + 'Z'

                with st.spinner(f"'{yt_query}' ({yt_region}, {date_range}) 관련 영상을 검색 중입니다..."):
                    # Initial search (sorting doesn't matter much here as we resort later, but fetching needed data)
                    long_forms, shorts = search_youtube_videos(
                        api_key, 
                        yt_query, 
                        max_results=yt_max,
                        region_code=yt_region,
                        published_after=published_after,
                        sort_by='trend' # Default fetch sort
                    )
                    
                    # Store in session state
                    st.session_state['yt_long_forms'] = long_forms
                    st.session_state['yt_shorts'] = shorts
                    st.session_state['yt_search_done'] = True
                    
    # Display Results (from Session State)
    if st.session_state.get('yt_search_done'):
        long_forms = st.session_state['yt_long_forms']
        shorts = st.session_state['yt_shorts']
        
        # Apply Sorting (Client-side)
        if sort_key == 'trend':
            long_forms.sort(key=lambda x: x['Score'], reverse=True)
            shorts.sort(key=lambda x: x['Score'], reverse=True)
        else: # viewCount
            long_forms.sort(key=lambda x: x['Views'], reverse=True)
            shorts.sort(key=lambda x: x['Views'], reverse=True)

        # 결과 표시
        if not long_forms and not shorts:
            st.warning("검색 결과가 없습니다.")
        else:
            if yt_search_btn: # Show success only on fresh search triggers to avoid annoyance
                st.success(f"검색 완료! 롱폼 {len(long_forms)}개, 숏폼 {len(shorts)}개 발견")
            
            col_long, col_short = st.columns(2)
            
            # 왼쪽: 롱폼
            with col_long:
                st.subheader(f"🎬 롱폼 영상 ({len(long_forms)})")
                if long_forms:
                    display_video_grid(long_forms, num_columns=2)
                else:
                    st.info("롱폼 영상이 없습니다.")
                    
            # 오른쪽: 숏폼
            with col_short:
                st.subheader(f"📱 숏폼 영상 ({len(shorts)})")
                if shorts:
                    display_video_grid(shorts, num_columns=2)
                else:
                    st.info("숏폼 영상이 없습니다.")

def page_naver_news():
    st.title("🗞️ 네이버 뉴스")
    
    # 탭으로 구분: 실시간 랭킹 / 뉴스 검색
    tab1, tab2 = st.tabs(["🔥 많이 본 뉴스 50", "🔍 뉴스 검색"])
    
    # --- Tab 1: 많이 본 뉴스 50 (Ranking) ---
    with tab1:
        col_head, col_btn = st.columns([4, 1])
        with col_head:
            st.subheader("언론사별 많이 본 뉴스 (Top 50)")
        with col_btn:
            if st.button("뉴스 새로고침", key='refresh_ranking'):
                st.cache_data.clear()
            
        # 데이터를 가져옵니다. (자동 로드)
        with st.spinner("많이 본 뉴스를 가져오는 중입니다..."):
            ranking_news = get_naver_ranking_news(limit=50)
            
        if ranking_news:
             # 데이터프레임으로 변환하여 표시
            df_ranking = pd.DataFrame(ranking_news)
            # 컬럼 순서 지정
            df_ranking = df_ranking[['Rank', 'Title', 'Link']]
            
            st.dataframe(
                df_ranking,
                use_container_width=True,
                column_config={
                    "Rank": st.column_config.NumberColumn("순위", width="small"),
                    "Title": st.column_config.TextColumn("제목", width="large"),
                    "Link": st.column_config.LinkColumn("링크", display_text="기사 보기")
                },
                hide_index=True
            )
        else:
            st.warning("랭킹 뉴스를 가져올 수 없습니다.")

    # --- Tab 2: 기존 검색 기능 ---
    with tab2:
        st.subheader("실시간 뉴스 검색")

    
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            news_query = st.text_input("검색어 입력", value="속보")
        with col2:
            news_sort = st.radio("정렬 기준", ('최신순', '관련도순'), horizontal=True)
        with col3:
            st.write("") # Spacer
            st.write("") 
            news_btn = st.button("뉴스 가져오기", use_container_width=True)
            
        if news_btn:
            client_id = st.secrets.get("NAVER_CLIENT_ID", "")
            client_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
            
            if not client_id or not client_secret:
                st.error("⚠️ 네이버 API 키가 없습니다.")
            else:
                sort_val = 'sim' if news_sort == '관련도순' else 'date'
                with st.spinner('뉴스를 가져오는 중...'):
                    news_list = get_naver_news_list(
                        client_id, client_secret, 
                        query=news_query, 
                        display=100, 
                        sort=sort_val
                    )
                    
                    if news_list:
                        st.success(f"{len(news_list)}개의 뉴스를 가져왔습니다.")
                        st.dataframe(
                            pd.DataFrame(news_list),
                            use_container_width=True,
                            column_config={
                                "Link": st.column_config.LinkColumn("Link", display_text="기사 이동"),
                                "Description": st.column_config.TextColumn("요약", width="large")
                            },
                            hide_index=True
                        )
                    else:
                        st.warning("검색 결과가 없습니다.")

def page_settings():
    st.title("⚙️ API 키 설정")
    st.markdown("`.streamlit/secrets.toml` 파일에 저장된 키를 확인하거나 임시로 입력할 수 있습니다.")
    st.warning("⚠️ 이곳에 입력한 내용은 페이지를 새로고침하면 초기화될 수 있습니다. 영구 저장을 위해선 `secrets.toml` 파일을 직접 수정하세요.")
    
    # Secrets 로드
    sec_yt = st.secrets.get("YOUTUBE_API_KEY", "")
    sec_nid = st.secrets.get("NAVER_CLIENT_ID", "")
    sec_nsc = st.secrets.get("NAVER_CLIENT_SECRET", "")
    
    with st.form("api_form"):
        st.subheader("YouTube Data API")
        new_yt = st.text_input("API Key", value=sec_yt, type="password")
        
        st.divider()
        
        st.subheader("Naver Developers API")
        new_nid = st.text_input("Client ID", value=sec_nid, type="password")
        new_nsc = st.text_input("Client Secret", value=sec_nsc, type="password")
        
        submitted = st.form_submit_button("설정 확인 및 테스트")
        
        if submitted:
            if new_yt and new_nid and new_nsc:
                st.success("✅ 키가 입력되어 있습니다. (실제 유효성 검사는 분석 시 진행됩니다)")
            else:
                st.error("❌ 일부 키가 누락되었습니다.")
            
            # 안내
            st.info(f"""
            **현재 로드된 설정:**
            - YouTube Key: {'✅ 설정됨' if sec_yt else '❌ 미설정'}
            - Naver ID: {'✅ 설정됨' if sec_nid else '❌ 미설정'}
            """)

# --- Navigation Setup ---
pg = st.navigation([
    st.Page(page_trend_analysis, title="트렌드 분석", icon="📊"),
    st.Page(page_youtube_analysis, title="유튜브 영상 분석", icon="🎥"),
    st.Page(page_naver_news, title="네이버 뉴스", icon="🗞️"),
    st.Page(page_settings, title="API 설정", icon="⚙️"),
])

pg.run()
