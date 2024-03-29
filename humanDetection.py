#!/usr/bin/env python3
import sys
if sys.version_info[0] < 3:
    raise Exception("Must be using Python 3")

from ctypes import *
import math
import random
import cv2
import numpy as np
import time
import os
import pyrealsense2 as rs
import select
import socket
import struct
import pickle


def sample(probs):
    s = sum(probs)
    probs = [a/s for a in probs]
    r = random.uniform(0, 1)
    for i in range(len(probs)):
        r = r - probs[i]
        if r <= 0:
            return i
    return len(probs)-1

def c_array(ctype, values):
    arr = (ctype*len(values))()
    arr[:] = values
    return arr

class BOX(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float),
                ("w", c_float),
                ("h", c_float)]

class DETECTION(Structure):
    _fields_ = [("bbox", BOX),
                ("classes", c_int),
                ("prob", POINTER(c_float)),
                ("mask", POINTER(c_float)),
                ("objectness", c_float),
                ("sort_class", c_int)]


class IMAGE(Structure):
    _fields_ = [("w", c_int),
                ("h", c_int),
                ("c", c_int),
                ("data", POINTER(c_float))]

class METADATA(Structure):
    _fields_ = [("classes", c_int),
                ("names", POINTER(c_char_p))]




class IplROI(Structure):
    pass

class IplTileInfo(Structure):
    pass

class IplImage(Structure):
    pass

IplImage._fields_ = [
    ('nSize', c_int),
    ('ID', c_int),
    ('nChannels', c_int),
    ('alphaChannel', c_int),
    ('depth', c_int),
    ('colorModel', c_char * 4),
    ('channelSeq', c_char * 4),
    ('dataOrder', c_int),
    ('origin', c_int),
    ('align', c_int),
    ('width', c_int),
    ('height', c_int),
    ('roi', POINTER(IplROI)),
    ('maskROI', POINTER(IplImage)),
    ('imageId', c_void_p),
    ('tileInfo', POINTER(IplTileInfo)),
    ('imageSize', c_int),
    ('imageData', c_char_p),
    ('widthStep', c_int),
    ('BorderMode', c_int * 4),
    ('BorderConst', c_int * 4),
    ('imageDataOrigin', c_char_p)]


class iplimage_t(Structure):
    _fields_ = [('ob_refcnt', c_ssize_t),
                ('ob_type',  py_object),
                ('a', POINTER(IplImage)),
                ('data', py_object),
                ('offset', c_size_t)]


#lib = CDLL("/home/pjreddie/documents/darknet/libdarknet.so", RTLD_GLOBAL)
lib = CDLL("darknet/libdarknet.so", RTLD_GLOBAL)
lib.network_width.argtypes = [c_void_p]
lib.network_width.restype = c_int
lib.network_height.argtypes = [c_void_p]
lib.network_height.restype = c_int

predict = lib.network_predict
predict.argtypes = [c_void_p, POINTER(c_float)]
predict.restype = POINTER(c_float)

set_gpu = lib.cuda_set_device
set_gpu.argtypes = [c_int]

make_image = lib.make_image
make_image.argtypes = [c_int, c_int, c_int]
make_image.restype = IMAGE

get_network_boxes = lib.get_network_boxes
get_network_boxes.argtypes = [c_void_p, c_int, c_int, c_float, c_float, POINTER(c_int), c_int, POINTER(c_int)]
get_network_boxes.restype = POINTER(DETECTION)

make_network_boxes = lib.make_network_boxes
make_network_boxes.argtypes = [c_void_p]
make_network_boxes.restype = POINTER(DETECTION)

free_detections = lib.free_detections
free_detections.argtypes = [POINTER(DETECTION), c_int]

free_ptrs = lib.free_ptrs
free_ptrs.argtypes = [POINTER(c_void_p), c_int]

network_predict = lib.network_predict
network_predict.argtypes = [c_void_p, POINTER(c_float)]

reset_rnn = lib.reset_rnn
reset_rnn.argtypes = [c_void_p]

load_net = lib.load_network
load_net.argtypes = [c_char_p, c_char_p, c_int]
load_net.restype = c_void_p

do_nms_obj = lib.do_nms_obj
do_nms_obj.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

do_nms_sort = lib.do_nms_sort
do_nms_sort.argtypes = [POINTER(DETECTION), c_int, c_int, c_float]

free_image = lib.free_image
free_image.argtypes = [IMAGE]

letterbox_image = lib.letterbox_image
letterbox_image.argtypes = [IMAGE, c_int, c_int]
letterbox_image.restype = IMAGE

load_meta = lib.get_metadata
lib.get_metadata.argtypes = [c_char_p]
lib.get_metadata.restype = METADATA

load_image = lib.load_image_color
load_image.argtypes = [c_char_p, c_int, c_int]
load_image.restype = IMAGE

rgbgr_image = lib.rgbgr_image
rgbgr_image.argtypes = [IMAGE]

predict_image = lib.network_predict_image
predict_image.argtypes = [c_void_p, IMAGE]
predict_image.restype = POINTER(c_float)


def classify(net, meta, im):
    out = predict_image(net, im)
    res = []
    for i in range(meta.classes):
        res.append((meta.names[i], out[i]))
    res = sorted(res, key=lambda x: -x[1])
    return res


def array_to_image(arr):
    # need to return old values to avoid python freeing memory
    arr = arr.transpose(2,0,1)
    c, h, w = arr.shape[0:3]
    arr = np.ascontiguousarray(arr.flat, dtype=np.float32) / 255.0
    data = arr.ctypes.data_as(POINTER(c_float))
    im = IMAGE(w,h,c,data)
    return im, arr


def detect(net, meta, image, thresh, hier_thresh, nms):
    """if isinstance(image, bytes):
        # image is a filename
        # i.e. image = b'/darknet/data/dog.jpg'
        im = load_image(image, 0, 0)
    else:
        # image is an nparray
        # i.e. image = cv2.imread('/darknet/data/dog.jpg')
        im, image = array_to_image(image)
        rgbgr_image(im)
    """
    im, image = array_to_image(image)
    rgbgr_image(im)
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(net, im.w, im.h, thresh,
                             hier_thresh, None, 0, pnum)
    num = pnum[0]
    if nms: do_nms_obj(dets, num, meta.classes, nms)

    res = []
    for j in range(num):
        a = dets[j].prob[0:meta.classes]
        if any(a):
            ai = np.array(a).nonzero()[0]
            for i in ai:
                b = dets[j].bbox
                res.append((meta.names[i], dets[j].prob[i],
                           (b.x, b.y, b.w, b.h)))

    res = sorted(res, key=lambda x: -x[1])
    if isinstance(image, bytes): free_image(im)
    free_detections(dets, num)
    return res


def runOnVideo(net, meta, vid_source):

    bbox_data = {
        'nboxes' : 0,
        'distance' : np.zeros(16,dtype=float),

    }

    RECEIVER_IP = "127.0.0.1"
    RECEIVER_PORT = 12345

    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 848, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    
    closestDist = 0.0

    try:
        while True:
            startTime = time.time()
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()

            #center_dist = depth_frame.get_distance(320,240)
            #print("center_dist",center_dist)

            
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            #print(depth_image.shape)

            r = detect(net, meta, color_image, thresh=0.75, hier_thresh=0.5, nms=0.45)
            #print(r)
            
            # Detect something
            if len(r) > 0:
                #print(r[0])
                i = 0
                
                for i in range(len(r)):
                    
                    className = str(r[i][0])        # Convert byte value to string
                    className = className[2:len(className)-1]   # This is to remove b'....' on name
                    #print("className",className)
                    
                    if className == 'person':
                        x = int(r[i][2][0]-r[i][2][2]/2)
                        y = int(r[i][2][1]-r[i][2][3]/2)
                        w = int(r[i][2][0]+r[i][2][2]/2)
                        h = int(r[i][2][1]+r[i][2][3]/2)
                        cv2.rectangle(color_image, (x, y), (w, h), (255,0,0), 2)
                        detectedOnFrame = (int(r[i][2][0]),int(r[i][2][1]))
                        Depth = depth_frame.get_distance(detectedOnFrame[0],detectedOnFrame[1])
                        #print(className + ' ' + str(Depth))
                        bbox_data['nboxes'] = i+1
                        bbox_data['distance'][i] = round(Depth,6)
                        tag = "ID: " + str(bbox_data['nboxes']) + "   Distance:" + str(bbox_data['distance'][i])
                        #putText on bbox
                        cv2.putText(color_image, tag,(x,y-10),cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,0), 2)
                        # Find the closest to print on screen
                        if np.max(bbox_data['distance'])>0:
                            closestDist = np.min(bbox_data['distance'][np.nonzero(bbox_data['distance'])])
                        else:
                            closestDist = 0.0
                        

                    else:
                        closestDist = 0.0
                        #cv2.putText(color_image, str(round(Depth,2)), (10, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        pass
                    
                    #cv2.imshow("Detected!", color_image)

            #depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
            #combineImages = np.hstack((color_image,depth_colormap))
            cv2.putText(color_image, str(round(closestDist,3)), (10, 450), cv2.FONT_HERSHEY_COMPLEX, 3, (0, 0, 0), 12, lineType=cv2.LINE_AA)    
            cv2.putText(color_image, str(round(closestDist,3)), (10, 450), cv2.FONT_HERSHEY_COMPLEX, 3, (255, 255, 255), 8, lineType=cv2.LINE_AA)
            
            cv2.imshow("Detected!", color_image)
            print("bbox_data['nboxes']", bbox_data['nboxes'])
            print("bbox_data['distance']",bbox_data['distance'])
            period = time.time()-startTime
            print("period",period)

            ##############
            # send out via UDP
            udpPacket = pickle.dumps(bbox_data)
            s.sendto(udpPacket,(RECEIVER_IP,RECEIVER_PORT))
            ##############

            # clear data off the array after send out via UDP
            bbox_data['nboxes'] = 0
            bbox_data['distance'] = np.zeros(16,dtype=float)

            cv2.waitKey(1)
            

    finally:
        pipeline.stop()





if __name__ == "__main__":

    net = load_net(b"darknet/cfg/yolov3-tiny.cfg", b"darknet/backup/yolov3-tiny.weights", 0)
    meta = load_meta(b"darknet/cfg/coco.data")
    vid_source = 0
    runOnVideo(net,meta,vid_source)
    #r = detect(net, meta, "data/dog.jpg")
    #print r
    

