#!/usr/bin/env python3

# Copyright 2019 Nina Marie Wahl and Charlotte Heggem.
# Copyright 2019 Norwegian University of Science and Technology.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import _thread as thread
import time
import sys
import serial
import binascii
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Point, Pose, Quaternion, Twist, Vector3, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from builtin_interfaces.msg import Time
from rclpy.qos import qos_profile_sensor_data
from rclpy.action import ActionServer, GoalResponse
from kuka_manipulator.action import OpenGripper
from kuka_manipulator.action import CloseGripper

from script.gripper_msgs import GripperMsg
from script.errorcodes import ErrorCodes


from enum import Enum
def cl_red(msge): return '\033[31m' + msge + '\033[0m'


class GripperNode(Node):
    def __init__(self):
        super().__init__('gripper_node')
        self.name='gripper_node'
        # TODO: change port to NUC
        self.ser = serial.Serial(port="/dev/ttyUSB1", baudrate=115200, timeout=1, parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
        self.activate()
        print("OK")
        self.open_action_server = ActionServer(self,OpenGripper,'open_gripper',self.open_gripper_callback)
        self.close_action_server = ActionServer(self, CloseGripper, 'close_gripper', self.close_gripper_callback)
    

    def open_gripper_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        self.open()
        while (self.isMoving()):
            pass
        result = OpenGripper.Result() 
        result.success = self.getOpenResponse()
        if result.success == True:
           goal_handle.succeed()
        else:
           goal_handle.abort()
        print("OK")
        return result

    def close_gripper_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        self.close()
        while (self.isMoving()):
            pass
        
        result = CloseGripper.Result()
        result.success = self.getClosedResponse()
        if result.success == True:
           goal_handle.succeed()
        else:
           goal_handle.abort()
        print("OK")
        return result


    def activate(self):
        # Activation Request
        self.ser.write(GripperMsg.Activation.value)
        data_raw = self.ser.readline()
        activated = False
        while (not activated):
            self.ser.write(GripperMsg.ActivationRequest.value)
            data_raw = self.ser.readline()
            data_string = binascii.hexlify(data_raw).decode()
            if (data_string == GripperMsg.ActivationComplete.value):
                activated = True
                self.close()
                self.open()

    def close(self):
        # Close the gripper
        self.ser.write(GripperMsg.CloseRequest.value)
        self.ser.readline()

    def open(self):
        # Open the gripper full speed and force
        self.ser.write(GripperMsg.OpenRequest.value)
        self.ser.readline()

    def isMoving(self):
        result=False
        self.ser.write(GripperMsg.StatusResponse.value)
        data_raw = self.ser.readline()
        gObj = self.messageTogObj(str(data_raw))
        # Not Moving
        if(gObj==GripperMsg.NOTMOVING.value):
            result=False
            print("Not moving")
        # Moving
        if(gObj==GripperMsg.MOVING.value):
            result=True
            print("Moving")
        return result

    def getClosedResponse(self):
        result = False
        self.ser.write(GripperMsg.StatusResponse.value)
        data_raw = self.ser.readline()
        gObj = self.messageTogObj(str(data_raw))
        # Closed, no object:
        if(gObj==GripperMsg.REQUESTEDPOSITION.value):
            result=False
            print(ErrorCodes.NO_OBJECT)
            # Closed, object:
        if(gObj==GripperMsg.OBJECT_CLOSING.value):
            result=True
            print(ErrorCodes.OBJECT_FOUND)
        return result

    def getOpenResponse(self):
        result=False
        self.ser.write(GripperMsg.StatusResponse.value)
        gObj = self.messageTogObj(str(self.ser.readline()))
        # Collision
        if (gObj == GripperMsg.OBJECT_OPENING.value):
            result = False
            print(ErrorCodes.COLLISION)
            # Open
        if (gObj == GripperMsg.REQUESTEDPOSITION.value):
            result = True
            print(ErrorCodes.OPEN)
        return result


    def messageTogObj(self, data_string):
        # moving only meaningful if gGTO = 1
        hexa = data_string.split("\\")[4].split("x")[1]
        binary = bin(int(hexa, 16))[2:].zfill(8)
        gGTO = binary[4]
        gObj = 2*int(binary[0]) + 1*int(binary[1])
        if (gObj==0 and gGTO!=1):
            gObj=-1
        return gObj

def main(args=None):
    rclpy.init(args=args)
    gripper_node = GripperNode()

    rclpy.spin(gripper_node)
    try:
        gripper_node.destroy_node()
        rclpy.shutdown()
    except:
        print(cl_red('Error: ') + "rclpy shutdown failed")



if __name__ == '__main__':
    main()
