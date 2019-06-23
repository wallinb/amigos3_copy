# # scheduling system
from schedule import schedule as schedule
import threading
import time
from datetime import datetime
from copy import deepcopy
from gps import gps_data as gps_data
from gpio import *
from vaisala import average_data as average_data
from onvif.onvif import *
from cr1000x import test as test
# import monitor as monitor


class summer():
    def __init__(self, *args, **kwargs):
        self.sched_summer = schedule.Scheduler()  # create a new schedule instance

    def vaisala_schedule(self):
        # Perform this measurement reading every hour between :58 to :00
        self.sched_semmer.every().hours.at(":58").do(average_data)  # add vaisala schedule

    def gps_schedule(self):
        gps = gps_data()
        # add gps schedules
        self.sched_summer.every().days.at("05:10").do(gps.get_binex)
        self.sched_summer.every().days.at("11:10").do(gps.get_binex)
        self.sched_summer.every().days.at("17:10").do(gps.get_binex)
        self.sched_summer.every().days.at("23:10").do(gps.get_binex)

    def camera_schedule(self):
        pass

    def cr100x_schedule(self):
        # add cr100 schedules
        self.sched_summer.every().hours.at(":55").do(test)

    def sched(self):
        # load all the schedules
        self.vaisala_schedule()
        self.camera_schedule()
        self.gps_schedule()
        self.cr100x_schedule()
        return self.shed_summer  # return the new loaded schedule


class winter():
    def __init__(self, *args, **kwargs):
        self.sched_winter = schedule.Scheduler()

    def vaisala_schedule(self):
        # Perform this measurement reading every hour between :58 to :00
        self.sched_winter.every().hours.at(":58").do(average_data)

    def gps_schedule(self):
        gps = gps_data()
        # add gps schedules
        self.sched_winter.every().days.at("23:10").do(gps.get_binex)

    def camera_schedule(self):
        pass

    def cr100x_schedule(self):
        # add cr100x schedules
        self.sched_winter.every().hours.at(":55").do(test)

    def sched(self):
        # load all the winter schedule
        self.vaisala_schedule()
        self.camera_schedule()
        self.gps_schedule()
        self.cr100x_schedule()
        return self.sched_winter


def run_schedule():
    # winter time frame
    winter_time = {'start': {'day': 1,
                             'month': 5},
                   'end': {'day': 31,
                           'month': 8}
                   }
    # summer time frame
    summer_time = {'start': {'day': 1,
                             'month': 9},
                   'end': {'day': 30,
                           'month': 4}
                   }
    # track thw rumming schedule
    winter_running = False
    summer_running = False
    # create a summer and winter schedule
    s = summer()
    w = winter()
    summer_task = s.sched()
    winter_task = w.sched()
    # run forever
    while True:
        # get the today date (tritron time must update to uptc time)
        today = datetime.datetime.now()
        # create datetime instance of winter and summer bracket
        winter_start = today.replace(
            month=winter_time['start']['month'], day=winter_time['start']['day'], hour=0, minute=0, second=0, microsecond=0)
        winter_end = today.replace(
            month=winter_time['end']['month'], day=winter_time['start']['day'], hour=23, minute=59, second=59, microsecond=0)
        summer_start = today.replace(
            month=summer_time['start']['month'], day=summer_time['start']['day'], hour=0, minute=0, second=0, microsecond=0)
        summer_end = today.replace(
            month=summer_time['end']['month'], day=summer_time['start']['day'], hour=23, minute=59, second=59, microsecond=0)
        # check if today falls into summer
        if summer_start < today <= summer_end:
            # do nothing if schedule is already running. This to avoid reloading the schedule arasing saved schedule
            if not summer_running:
                summer_running = True  # set flag
                s = summer()  # reload the schedule
                summer_task = s.sched()
                summer_task.run_pending()
                winter_task.clear()
                winter_running = False
                print('Started summer sched')
            else:
                summer_task.run_pending()
        # check if today falls into winter
        elif winter_start <= today < winter_end:
            if not winter_running:
                winter_running = True
                w = winter()
                summer_task.clear()
                winter_task = w.sched()
                winter_task.run_pending()
                summer_running = False
                print('Started winter sched')
            else:
                winter_task.run_pending()
        else:
            pass
        sleep(1)


# running this script start the schedule
if __name__ == "__main__":
    run_schedule()
