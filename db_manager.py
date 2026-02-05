import sqlite3
import pandas as pd
import json
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "deferred_storage.db")

def init_db():
    """DB 테이블 생성"""
    # data 폴더가 없으면 생성
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 스키마 변경을 위해 기존 테이블이 있다면 row_hash 컬럼 유무 등을 체크하기보다
    # 중복 허용 정책으로 변경되었으므로 깔끔하게 테이블을 새로 만드는 것이 안전함.
    # (주의: 기존에 쌓인 데이터가 날아감. 하지만 개발 단계이므로 허용)
    # 만약 데이터 보존이 중요하다면 ALTER TABLE을 써야 하지만 SQLite는 제한적임.
    # 여기서는 스키마가 바뀌었으므로 마이그레이션 대신 '테이블이 구버전이면 삭제' 로직을 넣거나
    # 그냥 항상 IF NOT EXISTS로 가되, 컬럼 에러가 나면 DROP하고 다시 만드는 식으로 처리.
    
    try:
        cursor.execute('SELECT row_hash FROM deferred_orders LIMIT 1')
        # row_hash 컬럼이 존재하면 구버전 테이블임 -> DROP
        cursor.execute('DROP TABLE deferred_orders')
    except sqlite3.Error:
        pass # 테이블이 없거나 row_hash 컬럼이 없으면 정상

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deferred_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nh_id INTEGER NOT NULL,
            json_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_deferred_data(df, nh_ids):
    """지정된 nh_id에 해당하는 데이터를 JSON으로 변환하여 저장"""
    if df.empty or not nh_ids:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved_count = 0
    
    # nh_id 별로 필터링하여 저장
    for nh_id in nh_ids:
        target_df = df[df['nh_id'] == nh_id]
        if target_df.empty:
            continue
            
        data_to_insert = []
        for _, row in target_df.iterrows():
            # 중복 방지 로직(Hashing) 제거됨
            # nh_id 컬럼은 제외하고 저장해도 되지만, 복원을 편하게 하기 위해 포함하거나
            # 여기서는 원본 그대로 저장 (nh_id는 DB 컬럼으로도 관리)
            json_data = row.to_json(force_ascii=False)
            data_to_insert.append((nh_id, json_data))
            
        # 중복 허용 (INSERT INTO ...)
        cursor.executemany('''
            INSERT INTO deferred_orders (nh_id, json_data)
            VALUES (?, ?)
        ''', data_to_insert)
        
        saved_count += cursor.rowcount
        
    conn.commit()
    conn.close()
    return saved_count

def load_pending_data(nh_id):
    """특정 업체의 보류 데이터 불러오기 -> DataFrame 반환"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT json_data FROM deferred_orders WHERE nh_id = ?
    ''', (nh_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return pd.DataFrame()
        
    # JSON 문자열 리스트 -> 데이터프레임 변환
    data_list = [json.loads(r[0]) for r in rows]
    return pd.DataFrame(data_list)

def delete_pending_data(nh_id):
    """처리 완료된 데이터 삭제"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM deferred_orders WHERE nh_id = ?', (nh_id,))
    conn.commit()
    conn.close()

def get_pending_counts():
    """각 업체별(nh_id) 보류 데이터 개수 반환 (dict)"""
    if not os.path.exists(DB_PATH):
        return {}
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nh_id, COUNT(*) FROM deferred_orders GROUP BY nh_id')
    rows = cursor.fetchall()
    conn.close()
    
    return {row[0]: row[1] for row in rows}
