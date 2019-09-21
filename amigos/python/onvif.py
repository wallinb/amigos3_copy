"""
Contains classes for  transport implementations.
"""
import datetime
import os
import subprocess
import traceback
from time import sleep

from execp import printf

# from xml.etree import ElementTree as et

# class urls():


class device_client:
    pass


class media_client:
    pass


class ptz_client:
    """
    PTZ client for ptz request, take picture, pan, tilt , and zoom.
    """

    def __init__(self):

        self.msg = None
        self.url = "http://192.168.0.108/onvif/ptz_service"
        self.header = None
        self.unit_degreePan = 0.0027777778 * 2
        self.unit_degreeTilt = 0.0055555556 * 4
        self.path = os.getcwd()
        self.snapShop_url = (
            "http://192.168.0.108/onvifsnapshot/media_service/snapshot?"
            "channel=1&subtype=0"
        )

    def __get_service(self, service):
        """[summary]

        Arguments:
            service {string} -- can be either relative or relative move to set
                the type of movement.
        """
        # the headers sent with request, the string format RelativeMove or AbsoluteMove
        self.headers = {
            "SOAPAction": "http://www.onvif.org/ver20/ptz/wsdl/{0}".format(
                service.capitalize() + "Move"
            ),
            "Content-Type": "application/soap+xml",
        }

    def __get_soap(self, service, pan=None, tilt=None, zoom=None):
        """get the soap (xml) file for the request. This the message to be sent

        Arguments:
            move {string} -- the move tosnapSho perform snapShot
        Keyword Arguments:snapSho
            service {string} -- the typesnapSho of move (default: {None})
            pan {float} -- the angle of snapShopan [-180 to 180 ].  (default: {None})
            tilt {float} -- the tilt possnapShoition [-4 to 45]. (default: {None})
            zoom {float} -- zoom value [-100 to 10]. (default: {None})
        """
        # print(service)

        if service is not None and service != "getstatus":

            with open(
                "/media/mmcblk0p1/amigos/onvif/soap_{0}.xml".format(service), "r"
            ) as soap:
                self.msg = soap.read()  # open the file
            # calculate the value of the pan  [-1 to 1]
            pan = pan * self.unit_degreePan
            # calculate the value of the tilt [-1 to 1]
            tilt = tilt * self.unit_degreeTilt
            # calculate the value of the soom  [-1 to 1]
            zoom = zoom / 100.0

            # format the requested pan.tilt and zoom into the message
            self.msg = self.msg.replace("{1}", str(tilt))
            self.msg = self.msg.replace("{2}", str(pan))
            if service == "AbsoluteMove":
                self.msg = self.msg.replace("{3}", str(zoom))
                self.msg = self.msg.replace("{4}", str(0))
            elif service == "RelativeMove":
                self.msg = self.msg.replace("{3}", str(0))
                self.msg = self.msg.replace("{4}", str(zoom))
                print("camera only support zoom in absolute mode")
            # print(zoom)

        # for the function get status
        else:
            with open(
                "/media/mmcblk0p1/amigos/onvif/soap_{0}.xml".format(service), "r"
            ) as soap:
                self.msg = soap.read()

    def send(self, typeof, pan=None, tilt=None, zoom=None):
        """send the http request to the camera

        Arguments:
            action {string} -- the movement to be made ex: tiltup
            typeof {string} -- the type of movement ex: ablsolute

        Keyword Arguments:
            pan {float} -- the angle of pan [-180 to 180 ].  (default: {None})
            tilt {float} -- the tilt position [-4 to 45]. (default: {None})
            zoom {float} -- zoom value [-100 to 10]. (default: {None})

        Returns:
            [instance] -- return the reply from the server as instance
        """
        # check if the input is not specified used the current value from the camera.
        try:
            from requests import post

            if pan is None:
                pan = float(self.getStatus()[0]) / self.unit_degreePan
            if tilt is None:
                tilt = float(self.getStatus()[1]) / self.unit_degreeTilt
            if zoom is None:
                zoom = float(self.getStatus()[2]) * 10
            # get the message body to be sent and apply all the value specified
            printf("To tilt {0},  pan {1} and zoom {2}".format(tilt, pan, zoom))
            self.__get_soap(
                service=typeof.capitalize() + "Move", pan=pan, tilt=tilt, zoom=zoom
            )

            # get apply the service to the header message
            self.__get_service(typeof)

            reply = post(self.url, data=self.msg, headers=self.header)

            return reply  # return the reply.
        except Exception:
            printf("Unable to communicate with camera``\\_(*_*)_/``")
            # traceback.print_exc(
            #     file=open("/media/mmcblk0p1/logs/system.log", "a+"))
            return None

    def getStatus(self, output=False):
        """Get the starus of the camera

        Returns:
            [floats] -- the current pan, tilt and the zoom
        """
        from requests import post

        self.__get_soap("getstatus")  # get the message for status
        printf("Getting camera status")
        self.header = {
            "SOAPAction": "http://www.onvif.org/ver20/ptz/wsdl/GetStatus",
            "Content-Type": "application/soap+xml",
        }  # The header of the status
        reply = post(
            self.url, data=self.msg, headers=self.header
        )  # reply is  an xml file
        # get the value of the pan, tilt and zoom from the text
        # print(reply.text)
        zoom = float(reply.text.split("><")[8].split('"')[3])
        pan = float(reply.text.split("><")[7].split('"')[3])
        tilt = float(reply.text.split("><")[7].split('"')[5])
        if not output:
            printf(
                (
                    "camera status: PAN_Position: {0}, "
                    "TITL_Position: {1}, "
                    "ZOOM_Position: {2}"
                ).format(pan, tilt, zoom)
            )
            return pan, tilt, zoom
        zoom = zoom * 100
        pan = pan / self.unit_degreePan
        tilt = tilt / self.unit_degreeTilt
        print(
            "PAN_Position: {0}\nTITL_Position: {1}\nZOOM_Position: {2}\n".format(
                pan, tilt, zoom
            )
        )

    def snapShot(self, size="3/8"):
        try:
            """
            get a snapshot
            """
            from monitor import reschedule
            from requests.auth import HTTPDigestAuth
            from requests import get

            printf("Camera Getting snapShot")
            dt = str(datetime.datetime.now()).split(" ")
            da = dt[0].split("-")
            da = "".join(da)
            ti = dt[1].split(":")
            ti = "".join(ti)
            dt = da + ti
            username = "admin"  # The cameras user name
            password = "10iLtxyh"  # the cameras password

            # send the username and password authentication
            response = get(self.snapShop_url, auth=HTTPDigestAuth(username, password))
            f = open("/media/mmcblk0p1/pic.jpg", "wb")  # opening

            # Write the file to the time stamp
            newname = "/media/mmcblk0p1/" + "picture" + dt[0:-7] + ".jpg"
            subprocess.call(
                "mv {0} {1}".format("/media/mmcblk0p1/pic.jpg", newname), shell=True
            )
            sleep(2)
            f.write(response.content)
            f.close()
            printf("Camera SnapShot taken :)")
            subprocess.call(
                "mv {0} {1}".format(newname, "/media/mmcblk0p1/unscaled_picture/"),
                shell=True,
            )
            sleep(1)
            printf("Resizing  SnapShot")
            sleep(1)
            subprocess.call(
                "resize_jpeg {0} {1} {2}".format(
                    size,
                    "/media/mmcblk0p1/unscaled_picture/"
                    + "picture"
                    + dt[0:-7]
                    + ".jpg",
                    "/media/mmcblk0p1/picture/" + "picture" + dt[0:-7] + ".jpg",
                ),
                shell=True,
            )
            printf("Resizing done!")
        except Exception:
            printf("Unable to take snapshot``\\_(*_*)_/``")
            reschedule(re="move")

    def move(self):
        try:
            from monitor import reschedule
            from gpio import modem_off, modem_on
            from monitor import timing
            from timeit import default_timer as timer

            start = timer()
            modem_on(1)
            sleep(5)
            printf("Camera moving north")
            self.send("absolute", pan=0, tilt=0, zoom=0)
            sleep(2)
            self.snapShot()
            sleep(1)
            printf("Camera moving east")
            self.send("absolute", pan=90, tilt=0, zoom=0)
            sleep(2)
            self.snapShot()
            sleep(1)
            printf("Camera moving west")
            self.send("absolute", pan=-90, tilt=0, zoom=0)
            sleep(2)
            self.snapShot()
            sleep(1)
            printf("Camera moving down")
            self.send("absolute", pan=0, tilt=-45, zoom=0)
            sleep(2)
            self.snapShot()
            printf("Camera moving to mirror")
            self.send("absolute", pan=0, tilt=-45, zoom=100)
            sleep(2)
            self.snapShot()
            printf("Done! Sending camera lens to Home")
            sleep(1)
            self.send("absolute", pan=0, tilt=45, zoom=0)
            reschedule(run="move")
            end = timer()
            timing("move", end - start)
        except Exception:
            printf("Camera failed to take picture")
            reschedule(re="move")
            traceback.print_exc(file=open("/media/mmcblk0p1/logs/system.log", "a+"))
        finally:
            modem_off(1)


# Test the code here
# if __name__ == "__main__":
#     ptz = ptz_client()
#     ptz.send(typeof='relative',
#              pan=25, tilt=0, zoom=0)
#     sleep(2)
#     ptz.snapShot()dts_data
#     sleep(1)
#     ptz.getStatus()
#     t1 = time.time()