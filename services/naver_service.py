
import requests
import re
import streamlit as st
from bs4 import BeautifulSoup

def get_naver_ranking_news(limit=50):
    """
    네이버 뉴스 랭킹 페이지를 크롤링하여 많이 본 뉴스를 반환합니다.
    URL: https://news.naver.com/main/ranking/popularDay.naver
    """
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            st.error(f"네이버 랭킹 뉴스 가져오기 실패: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 'a.list_title' 셀렉터를 사용하여 뉴스 제목과 링크 추출
        # 이 페이지는 언론사별 랭킹박스가 있고 그 안에 리스트가 있음
        news_items = []
        
        # 모든 랭킹 뉴스 링크 추출 (보통 페이지에 많은 뉴스가 있지만 상위 50개만 자름)
        # 네이버 구조상 언론사별 Top 5가 쭉 나열됨. 이를 전체 리스트로 모아서 반환.
        # 사용자의 요구는 "많이 본 뉴스 50개"이므로 페이지 순서대로 50개를 가져옴.
        links = soup.select('a.list_title')
        
        for link in links[:limit]:
            title = link.text.strip()
            href = link.get('href')
            
            if href:
                news_items.append({
                    'Title': title,
                    'Link': href,
                    'Rank': len(news_items) + 1
                })
                
        return news_items
        
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {e}")
        return []

def get_naver_trending_topics(client_id, client_secret, category='news', max_results=100, sort='date', custom_query=None):
    """
    네이버 뉴스 검색 API를 사용하여 트렌드 키워드를 추출합니다.
    category: 'news' (뉴스) 또는 'sports' (스포츠)
    sort: 'date' (최신순) 또는 'sim' (관련도순)
    custom_query: 사용자 정의 검색어 (None이면 카테고리 기본값 사용)
    """
    # 카테고리별 기본 검색 쿼리
    query_map = {
        'news': '최신',
        'sports': '스포츠'
    }
    
    # 검색어 결정: 사용자 입력이 있으면 우선 사용
    if custom_query and custom_query.strip():
        query = custom_query
    else:
        query = query_map.get(category, '최신')
        
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    params = {
        "query": query,
        "display": max_results,
        "sort": sort
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            # 기사 제목에서 키워드 추출
            all_words = []
            article_data = []
            
            for item in items:
                title = item['title']
                # HTML 태그 제거
                clean_title = re.sub(r'<[^>]+>', '', title)
                # 한글만 추출 (2글자 이상)
                words = re.findall(r'[가-힣]{2,}', clean_title)
                all_words.extend(words)
                
                article_data.append({
                    'Title': clean_title,
                    'Link': item.get('link', '')
                })
            
            return all_words, article_data
        else:
            st.error(f"네이버 API 오류: {response.status_code} - {response.text}")
            return [], []
            
    except Exception as e:
        st.error(f"네이버 API 호출 중 오류 발생: {e}")
        return [], []

def get_naver_news_list(client_id, client_secret, query='최신', display=100, sort='date'):
    """
    네이버 뉴스 검색 API를 사용하여 뉴스 리스트를 반환합니다.
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    
    params = {
        "query": query,
        "display": display,
        "sort": sort
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            
            news_list = []
            
            for item in items:
                title = item['title']
                description = item['description']
                
                # HTML 태그 제거
                clean_title = re.sub(r'<[^>]+>', '', title)
                clean_desc = re.sub(r'<[^>]+>', '', description)
                
                news_list.append({
                    'Title': clean_title,
                    'Description': clean_desc,
                    'Date': item.get('pubDate', ''),
                    'Link': item.get('originallink') or item.get('link', '')
                })
            
            return news_list
        else:
            st.error(f"네이버 API 오류: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        st.error(f"네이버 API 호출 중 오류 발생: {e}")
        return []
