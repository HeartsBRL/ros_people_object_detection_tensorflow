#!/usr/bin/env python
"""
A ROS node to get 3D values of bounding boxes returned by face_recognizer node.

This node gets the face bounding boxes and gets the real world coordinates of
them by using depth values. It simply gets the x and y values of center point
and gets the median value of face depth values as z value of face.

Author:
    Cagatay Odabasi -- cagatay.odabasi@ipa.fraunhofer.de
"""

import rospy

import message_filters

import math

import numpy as np

from cv_bridge import CvBridge

from sensor_msgs.msg import Image

from cob_perception_msgs.msg import DetectionArray


class ProjectionNode(object):
    """Get 3D values of bounding boxes returned by face_recognizer node.

    _bridge (CvBridge): Bridge between ROS and CV image
    pub (Publisher): Publisher object for face depth results
    f (Float): Focal Length
    cx (Int): Principle Point Horizontal
    cy (Int): Principle Point Vertical

    """
    def __init__(self):
        super(ProjectionNode, self).__init__()

        # init the node
        rospy.init_node('projection_node', anonymous=False)

        self._bridge = CvBridge()

        (depth_topic, face_topic, output_topic, f, cx, cy, RF) = \
            self.get_parameters()

         # Subscribe to the face positions
        sub_obj = message_filters.Subscriber(face_topic,\
            DetectionArray)

        sub_depth = message_filters.Subscriber(depth_topic,\
            Image)

        # Advertise the result of Face Depths
        self.pub = rospy.Publisher(output_topic, \
            DetectionArray, queue_size=1)

        # Create the message filter
        ts = message_filters.ApproximateTimeSynchronizer(\
            [sub_obj, sub_depth], \
            4, \
            1)

        ts.registerCallback(self.detection_callback)

        self.f = f
        self.cx = cx
        self.cy = cy
        self.rf = RF
        # spin
        rospy.spin()


    def shutdown(self):
        """
        Shuts down the node
        """
        rospy.signal_shutdown("See ya!")

    def detection_callback(self, msg, depth):
        """
        Callback for RGB images: The main logic is applied here

        Args:
        msg (cob_perception_msgs/DetectionArray): detections array
        depth (sensor_msgs/PointCloud2): depth image from camera

        """

        cv_depth = self._bridge.imgmsg_to_cv2(depth, "passthrough")

        # get the number of detections
        no_of_detections = len(msg.detections)

        # Check if there is a detection
        if no_of_detections > 0:
            for i, detection in enumerate(msg.detections):

                x =  detection.mask.roi.x
                y = detection.mask.roi.y
# DANIEL HEARTS TEAM MODIFICATION (Reduce width and height of the bounding box to avoid background depth values from influencing the mean)
                #RF = 0.8
                width =  int(round(detection.mask.roi.width*self.rf))
                height = int(round(detection.mask.roi.height*self.rf))

                cv_depth = cv_depth[y:y+height,x:x+width]

                # depth_mean = np.nanmedian(cv_depth[np.nonzero(cv_depth)])

                try:

                    depth_mean = np.nanmedian(cv_depth[np.nonzero(cv_depth)])

# DANIEL HEARTS TEAM MODIFICATION (Remove the 0.001 factor as it apparently publishes coordiantes in kilometers) Without 0.001 is meters

                    real_x = (x + width/2-self.cx)*(depth_mean)/self.f#*0.001)/self.f

                    real_y = (y + height/2-self.cy)*(depth_mean)/self.f#*0.001)/self.f

                    if math.isnan(real_x) or math.isnan(real_y) or math.isnan(depth_mean):
                        msg.detections[i].pose.pose.position.x = 0
                        msg.detections[i].pose.pose.position.y = 0
                        msg.detections[i].pose.pose.position.z = 100#*0.001
                        print "real_x: " + str(math.isnan(real_x))
                        print "real_y: " + str(math.isnan(real_y))
                        print "depth-mean: " + str(math.isnan(depth_mean))
                    else:
                        msg.detections[i].pose.pose.position.x = real_x
                        msg.detections[i].pose.pose.position.y = real_y
                        msg.detections[i].pose.pose.position.z = depth_mean#*0.001

                except Exception as e:
                    print e

        self.pub.publish(msg)

    def get_parameters(self):
        """
        Gets the necessary parameters from parameter server

        Returns:
        (tuple) :
            depth_topic (String): Incoming depth topic name
            face_topic (String): Incoming face bounding box topic name
            output_topic (String): Outgoing depth topic name
            f (Float): Focal Length
            cx (Int): Principle Point Horizontal
            cy (Int): Principle Point Vertical
        """

        depth_topic  = rospy.get_param("~depth_topic")
        face_topic = rospy.get_param('~face_topic')
        output_topic = rospy.get_param('~output_topic')
        f = rospy.get_param('~focal_length')
        cx = rospy.get_param('~cx')
        cy = rospy.get_param('~cy')
        RF = rospy.get_param('~RF')

        return (depth_topic, face_topic, output_topic, f, cx, cy, RF)


def main():
    """ main function
    """
    node = ProjectionNode()

if __name__ == '__main__':
    main()
