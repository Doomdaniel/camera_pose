#! /usr/bin/env python

import roslib
roslib.load_manifest('megacal_estimation')

import sys, time, optparse
import itertools
import collections
import rospy
import threading
import PyKDL

from tf_conversions import posemath
from std_msgs.msg import Empty
from megacal_estimation.msg import CalibrationEstimate
from megacal_estimation.msg import CameraPose
from calibration_msgs.msg import RobotMeasurement
from megacal_estimation.msg import CameraCalibration
from megacal_estimation import init_optimization_prior
from megacal_estimation import estimate


class Estimator:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()
        self.pub = rospy.Publisher('camera_calibration', CameraCalibration)
        self.sub_reset = rospy.Subscriber('reset', Empty, self.reset_cb)
        self.sub_meas  = rospy.Subscriber('robot_measurement', RobotMeasurement, self.meas_cb)

    def reset_cb(self, msg):
        self.reset()

    def reset(self):
        with self.lock:
            self.state = None
            self.meas = []
            rospy.loginfo('Reset calibration state')


    def meas_cb(self, msg):
        with self.lock:
            # add measurements to list
            self.meas.append(msg)
            print "MEAS", len(self.meas)

            # initialize state if needed
            if not self.state:
                self.state = CalibrationEstimate()
                print "STATE",self.state
                camera_poses, checkerboard_poses = init_optimization_prior.find_initial_poses(self.meas)
                self.state.targets = [ posemath.toMsg(checkerboard_poses[i]) for i in range(len(checkerboard_poses)) ]
                self.state.cameras = [ CameraPose(camera_id, posemath.toMsg(camera_pose)) for camera_id, camera_pose in camera_poses.iteritems()]

            # run optimization
            self.state = estimate.enhance(self.meas, self.state)

            # publish calibration state
            res = CameraCalibration()
            res.camera_pose = [camera.pose for camera in self.state.cameras]
            res.camera_id = [camera.camera_id for camera in self.state.cameras]
            self.pub.publish(res)


def main():
    rospy.init_node('online_calibration')
    e = Estimator()
    
    rospy.spin()

if __name__ == '__main__':
    main()


