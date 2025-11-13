"""스케줄러 메인 스크립트"""
import schedule
import time
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from config.settings import settings
from scheduler.src.worker import CrawlerWorker


def run_crawler():
    """크롤러 실행"""
    worker = CrawlerWorker()
    asyncio.run(worker.run_crawl_job())


def main():
    """스케줄러 메인 함수"""
    # 2시간마다 크롤링 실행
    schedule.every(settings.scheduler_interval_hours).hours.do(run_crawler)
    
    # 시작 시 즉시 실행
    run_crawler()
    
    # 스케줄러 실행
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 확인


if __name__ == "__main__":
    main()









