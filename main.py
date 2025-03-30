"""
PeopleCounter 메인 실행 모듈
"""

import cv2
import config

from counter import PeopleCounter
from visualizer import Visualizer
from detector import ObjectDetector
from helper import create_video_writer


def main():
    """
    메인 실행 함수
    """
    # 비디오 캡처 및 출력 설정
    cap = cv2.VideoCapture(config.INPUT_VIDEO_PATH)
    if not cap.isOpened():
        print(f"오류: 비디오 파일을 열 수 없습니다. ({config.INPUT_VIDEO_PATH})")
        return
    
    writer = create_video_writer(cap, config.OUTPUT_VIDEO_PATH)
    
    # 객체 초기화
    detector = ObjectDetector(config.MODEL_PATH)
    counter = PeopleCounter()
    visualizer = Visualizer()
    
    print(f"처리 중: {config.INPUT_VIDEO_PATH}")
    print(f"출력 파일: {config.OUTPUT_VIDEO_PATH}")
    print("종료하려면 'q' 키를 누르세요.")
    
    frame_count = 0
    
    while True:
        # 비디오 프레임 읽기
        success, frame = cap.read()
        if not success:
            print("비디오 처리 완료")
            break
        
        frame_count += 1
        
        # 객체 감지 수행
        boxes_info, detections = detector.detect(frame)
        
        # 객체 추적 및 카운팅
        tracking_results, activated_lines = counter.update(detections)
        
        # 카운트 정보 가져오기
        count_up, count_down = counter.get_counts()
        
        # 시각화
        frame = visualizer.draw_detection_boxes(frame, boxes_info)
        frame = visualizer.draw_tracking_boxes(frame, tracking_results)
        frame = visualizer.draw_counting_lines(frame, activated_lines)
        frame = visualizer.draw_count_info(frame, count_up, count_down)
        
        # 프레임 번호 표시
        cv2.putText(frame, f"Frame: {frame_count}", (20, 120), 
                    cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 255, 255), 2)
        
        # 프레임 표시 및 저장
        cv2.imshow("People Counter", frame)
        writer.write(frame)
        
        # 'q' 키를 누르면 종료
        if cv2.waitKey(1) == ord("q"):
            print("사용자에 의해 중단됨")
            break
    
    # 모든 리소스 해제
    cap.release()
    writer.release()
    cv2.destroyAllWindows()
    
    print(f"최종 카운트 - 상향: {count_up}, 하향: {count_down}")


if __name__ == "__main__":
    main()

