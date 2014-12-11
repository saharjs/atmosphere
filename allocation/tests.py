from allocation.engine import calculate_allocation
from allocation.models import Provider, Machine, Size, Instance, InstanceHistory
from core.models import Instance as CoreInstance
from allocation.models import Allocation,\
        MultiplySizeCPU, MultiplySizeRAM,\
        MultiplySizeDisk, MultiplyBurnTime,\
        AllocationIncrease, AllocationRecharge, TimeUnit,\
        IgnoreStatusRule, CarryForwardTime
from django.test import TestCase
from django.utils.timezone import datetime, timedelta
import pytz

#For testing..
openstack = Provider(
        name="iPlant Cloud - Tucson",
        identifier="4")
openstack_workshop = Provider(
        name="iPlant Cloud Workshop - Tucson",
        identifier="5")
random_machine = Machine(
        name="Not real machine",
        identifier="12412515-1241-3fc8-bc13-10b03d616c54")
random_machine_2 = Machine(
        name="Not real machine",
        identifier="39966e54-9282-4fc8-bc13-10b03d616c54")
tiny_size = Size(name='Kids Fry', identifier='test.tiny', cpu=1, ram=1024*2, disk=0)
small_size = Size(name='Small Fry', identifier='test.small', cpu=2, ram=1024*8, disk=60)
medium_size = Size(name='Medium Fry', identifier='test.medium', cpu=4, ram=1024*16, disk=120)
large_size = Size(name='Large Fry', identifier='test.large', cpu=8, ram=1024*32, disk=240)



# Rules
carry_forward = CarryForwardTime()

multiply_by_ram = MultiplySizeRAM(
        name="Multiply TimeUsed by Ram (*1GB)", multiplier=(1/1024))
multiply_by_cpu = MultiplySizeCPU(
        name="Multiply TimeUsed by CPU", multiplier=1)
multiply_by_disk = MultiplySizeDisk(
        name="Multiply TimeUsed by Disk", multiplier=1)

half_usage_by_ram = MultiplySizeRAM(
        name="Multiply TimeUsed by 50% of Ram (GB)",
        multiplier=.5*(1/1024) )
half_usage_by_cpu =  MultiplySizeCPU(
        name="Multiply TimeUsed by 50% of CPU",
        multiplier=.5)
half_usage_by_disk = MultiplySizeDisk(
        name="Multiply TimeUsed by 50% of Disk",
        multiplier=.5)

zero_burn_rate = MultiplyBurnTime(name="Stop all Total Time Used", multiplier=0.5)
half_burn_rate = MultiplyBurnTime(name="Half-Off Total Time Used", multiplier=0.5)
double_burn_rate = MultiplyBurnTime(name="Double Total Time Used", multiplier=2.0)

ignore_suspended = IgnoreStatusRule("Ignore Suspended Instances", "suspended")
ignore_build = IgnoreStatusRule("Ignore 'Build' Instances", "build")

def return_results():
    return [
            run_test1(),
            run_test2(),
           ]

#Dynamic Tests
def test_instances(instance_ids, start_window, end_window, credits=[]):
    """
    """
    instance_list = []
    for instance_id in instance_ids:
        core_instance = CoreInstance.objects.get(provider_alias=instance_id)
        instance_list.append(Instance.from_core(core_instance))
    allocation_test = Allocation(
        credits=credits,
        rules=[
            #Instance Rules
            #*4 with medium_size
            multiply_by_cpu,
            ignore_suspended,
            ignore_build,
            ],
        instances=instance_list,
        start_date=start_window, end_date=end_window
    )
    allocation_result = calculate_allocation(allocation_test)
    return allocation_result

#Static tests
def run_test1():
    """
    Test 1:
    Window set at 5 months (7/1/14 - 12/1/14)
    One-time credit of 10,000 AU (7/1)
    Instance swaps from active/suspended
     every 3 days for 5 months starting (7/4/14 @ 12:00)
    Real world answer:
    * 153 days between 12/1 and 7/1
    * Each history_interval is 3 days long (153/3 = 51 status changes)
    * Starting with active, that means 75 days of 'clock time'
    * Using a CPURule && 4CPU Size on 75 days == 300 days total usage
    """
    window_start = datetime(2014,7,1, tzinfo=pytz.utc)
    window_stop = datetime(2014,12,1, tzinfo=pytz.utc)
    swap_days = timedelta(3)
    history_start = datetime(2014,7,4,hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014,12,4,hour=12, tzinfo=pytz.utc)
    achieve_greatness = AllocationIncrease(name="Add 10,000 Hours ",
            unit=TimeUnit.hour, amount=10000, increase_date=history_start)
    history_list = []
    is_active = True
    history_next = history_start + swap_days
    while history_next < history_stop:
        new_history = InstanceHistory(
             status="active" if is_active else "suspended",
             size=medium_size,
             start_date=history_start,
             end_date=history_start+swap_days)
        history_list.append(new_history)
        #Toggle/Update..
        is_active = not is_active
        history_start = history_next
        history_next += timedelta(days=3)
    running_instance = Instance(
            identifier="TestInst-ance-1_____________________",
            provider=openstack, machine=random_machine,
            history=history_list)

    allocation_test_1 = Allocation(
        credits=[achieve_greatness],
        rules=[
            #Instance Rules
            multiply_by_cpu, #*4 with medium_size
            ignore_suspended,
            ignore_build,
            ],
        instances=[running_instance,],
        start_date=window_start, end_date=window_stop
    )
    allocation_result = calculate_allocation(allocation_test_1)
    return allocation_result

def run_test2():
    """
    Test 1:
    NEW FEATURE: INTERVAL 21 days + CarryForwardTime rule added

    Window set at 5 months (7/1/14 - 12/1/14)
    One-time credit of 10,000 AU (7/1)
    Instance swaps from active/suspended
     every 3 days for 5 months starting (7/4/14 @ 12:00)
    Real world answer:
    * 153 days between 12/1 and 7/1
    * Each history_interval is 3 days long (153/3 = 51 status changes)
    * Starting with active, that means 75 days of 'clock time'
    * Using a CPURule && 4CPU Size on 75 days == 300 days total usage
    """
    window_start = datetime(2014,7,1, tzinfo=pytz.utc)
    window_stop = datetime(2014,12,1, tzinfo=pytz.utc)
    swap_days = timedelta(3)
    interval_days = timedelta(21)
    history_start = datetime(2014,7,4,hour=12, tzinfo=pytz.utc)
    history_stop = datetime(2014,12,4,hour=12, tzinfo=pytz.utc)
    achieve_greatness = AllocationIncrease(name="Add 10,000 Hours ",
            unit=TimeUnit.hour, amount=10000, increase_date=history_start)
    history_list = []
    is_active = True
    history_next = history_start + swap_days
    while history_next < history_stop:
        new_history = InstanceHistory(
             status="active" if is_active else "suspended",
             size=medium_size,
             start_date=history_start,
             end_date=history_start+swap_days)
        history_list.append(new_history)
        #Toggle/Update..
        is_active = not is_active
        history_start = history_next
        history_next += timedelta(days=3)
    running_instance = Instance(
            identifier="TestInst-ance-1_____________________",
            provider=openstack, machine=random_machine,
            history=history_list)

    allocation_test_1 = Allocation(
        credits=[achieve_greatness],
        rules=[
            #Instance Rules
            multiply_by_cpu, #*4 with medium_size
            carry_forward,
            ignore_suspended,
            ignore_build,
            ],
        instances=[running_instance,],
        start_date=window_start, end_date=window_stop,
        interval_delta=interval_days
    )
    allocation_result = calculate_allocation(allocation_test_1)
    return allocation_result

"""
Examples I think will break things:
    1. start_date = 1/1, end_date = 1/31
    2. Instances use 7 days of allocation from 1/1 to 1/8
    3. User has his monthly allocation on 1/8 (14 days)
    4. Instances use 7 days of allocation from 1/8 to 1/15
Questions:
    2. What "AllocationIncreases" are valid if the dates occur PRIOR to the
    recharge_date?
       * I think they should be ignored, and given a new AllocationIncrease
       * with the remainder value (The amount of that increase used in the
       * month PRIOR).
    # Should step 2 be allowed in the engine, should invalid time periods flag
    # in some way??
"""
