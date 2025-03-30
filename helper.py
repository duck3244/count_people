import cv2


def create_video_writer(video_cap, output_filename):
    """
    Create a video writer object based on the properties of the input video capture.
    
    Args:
        video_cap: cv2.VideoCapture object
        output_filename: Name of the output video file
        
    Returns:
        cv2.VideoWriter object
    """
    # Grab the width, height, and fps of the frames in the video stream
    frame_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(video_cap.get(cv2.CAP_PROP_FPS))

    # Initialize the FourCC and a video writer object
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    writer = cv2.VideoWriter(output_filename, fourcc, fps,
                             (frame_width, frame_height))

    return writer

