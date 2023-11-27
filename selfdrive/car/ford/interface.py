from os import path
from openpilot.common.params import Params
import json

from cereal import car
from panda import Panda
from openpilot.common.conversions import Conversions as CV
from openpilot.selfdrive.car import get_safety_config, create_mads_event
from openpilot.selfdrive.car.ford.fordcan import CanBus
from openpilot.selfdrive.car.ford.values import CANFD_CAR, CAR, Ecu, BUTTON_STATES
from openpilot.selfdrive.car.interfaces import CarInterfaceBase

ButtonType = car.CarState.ButtonEvent.Type
TransmissionType = car.CarParams.TransmissionType
GearShifter = car.CarState.GearShifter


class CarInterface(CarInterfaceBase):
  def __init__(self, CP, CarController, CarState):
    super().__init__(CP, CarController, CarState)

    self.buttonStatesPrev = BUTTON_STATES.copy()

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, experimental_long, docs):
    data = {}
    jsonFile = Params().get_param_path() + "/../F150Tuning.json"
    if path.exists(jsonFile):
      f = open(jsonFile)
      data = json.load(f)
      f.close()

    ret.carName = "ford"

    ret.dashcamOnly = candidate in {CAR.F_150_MK14} 
    if 'dashcamOnly' in data:
      ret.dashcamOnly = data['dashcamOnly']
    
    ret.radarUnavailable = True
    if 'radarUnavailable' in data:
      ret.radarUnavailable = data['radarUnavailable']

    ret.steerControlType = car.CarParams.SteerControlType.angle

    ret.steerActuatorDelay = 0.2
    if 'steerActuatorDelay' in data:
      ret.steerActuatorDelay = data['steerActuatorDelay']

    ret.steerLimitTimer = 1.0

    if 'longitudinalTuning_deadzoneBP' in data:
      ret.longitudinalTuning.deadzoneBP = data['longitudinalTuning_deadzoneBP']
      # ret.longitudinalTuning.deadzoneBP = [0., 9.]

    if 'longitudinalTuning_deadzoneV' in data:
      ret.longitudinalTuning.deadzoneV = data['longitudinalTuning_deadzoneV']    
      # ret.longitudinalTuning.deadzoneV = [.0, .20]

    if 'stoppingControl' in data:
      ret.stoppingControl = data['stoppingControl']
      # ret.stoppingControl = True

    if 'startingState' in data:
      ret.startingState = data['startingState']
      # ret.startingState = True

    if 'startAccel' in data:
      ret.startAccel = data['startAccel']
      # ret.startAccel = 1.0

    if 'vEgoStarting' in data:
      ret.vEgoStarting = data['vEgoStarting']
      # ret.vEgoStarting = 1.0

    if 'vEgoStopping' in data:
      ret.vEgoStopping = data['vEgoStopping']
      # ret.vEgoStopping = 1.0
    
    if 'longitudinalActuatorDelayLowerBound' in data:
      ret.longitudinalActuatorDelayLowerBound = data['longitudinalActuatorDelayLowerBound']
      # ret.longitudinalActuatorDelayLowerBound = 0.5

    if 'longitudinalActuatorDelayUpperBound' in data:
      ret.longitudinalActuatorDelayUpperBound = data['longitudinalActuatorDelayUpperBound']
      # ret.longitudinalActuatorDelayUpperBound = 0.5

    if 'stopAccel' in data:
      ret.stopAccel = data['stopAccel']
      # ret.stopAccel = -2.0

    if 'stoppingDecelRate' in data:
      ret.stoppingDecelRate = data['stoppingDecelRate']
      # ret.stoppingDecelRate = 0.05

    if 'longitudinalTuning_kf' in data:
      ret.longitudinalTuning.kf = data['longitudinalTuning_kf']
    if 'longitudinalTuning_kpBP' in data:
      ret.longitudinalTuning.kpBP = data['longitudinalTuning_kpBP']
    if 'longitudinalTuning_kpV' in data:
      ret.longitudinalTuning.kpV = data['longitudinalTuning_kpV']
    if 'longitudinalTuning_kiBP' in data:
      ret.longitudinalTuning.kiBP = data['longitudinalTuning_kiBP']
    if 'longitudinalTuning_kiV' in data:
      ret.longitudinalTuning.kiV = data['longitudinalTuning_kiV']


    CAN = CanBus(fingerprint=fingerprint)
    cfgs = [get_safety_config(car.CarParams.SafetyModel.ford)]
    if CAN.main >= 4:
      cfgs.insert(0, get_safety_config(car.CarParams.SafetyModel.noOutput))
    ret.safetyConfigs = cfgs

    ret.experimentalLongitudinalAvailable = True
    if experimental_long:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_FORD_LONG_CONTROL
      ret.openpilotLongitudinalControl = True

    if candidate in CANFD_CAR:
      ret.safetyConfigs[-1].safetyParam |= Panda.FLAG_FORD_CANFD

    if candidate == CAR.BRONCO_SPORT_MK1:
      ret.wheelbase = 2.67
      ret.steerRatio = 17.7
      ret.mass = 1625

    elif candidate == CAR.ESCAPE_MK4:
      ret.wheelbase = 2.71
      ret.steerRatio = 16.7
      ret.mass = 1750

    elif candidate == CAR.EXPLORER_MK6:
      ret.wheelbase = 3.025
      ret.steerRatio = 16.8
      ret.mass = 2050

    elif candidate == CAR.F_150_MK14:
      # required trim only on SuperCrew
      ret.wheelbase = 145.4 * 0.0254
      ret.steerRatio = 17.4
      ret.mass = 4501 * CV.LB_TO_KG

    elif candidate == CAR.FOCUS_MK4:
      ret.wheelbase = 2.7
      ret.steerRatio = 15.0
      ret.mass = 1350

    elif candidate == CAR.MAVERICK_MK1:
      ret.wheelbase = 3.076
      ret.steerRatio = 17.0
      ret.mass = 1650

    else:
      raise ValueError(f"Unsupported car: {candidate}")

    if 'wheelbase' in data:
      ret.wheelbase = data['wheelbase']

    if 'steerRatio' in data:
      ret.steerRatio = data['steerRatio']

    if 'mass' in data:
      ret.mass = data['mass']

    # Auto Transmission: 0x732 ECU or Gear_Shift_by_Wire_FD1
    found_ecus = [fw.ecu for fw in car_fw]
    if Ecu.shiftByWire in found_ecus or 0x5A in fingerprint[CAN.main] or docs:
      ret.transmissionType = TransmissionType.automatic
    else:
      ret.transmissionType = TransmissionType.manual
      ret.minEnableSpeed = 20.0 * CV.MPH_TO_MS

    # BSM: Side_Detect_L_Stat, Side_Detect_R_Stat
    # TODO: detect bsm in car_fw?
    ret.enableBsm = 0x3A6 in fingerprint[CAN.main] and 0x3A7 in fingerprint[CAN.main]

    # LCA can steer down to zero
    ret.minSteerSpeed = 0.

    ret.autoResumeSng = ret.minEnableSpeed == -1.
    ret.centerToFront = ret.wheelbase * 0.44
    return ret

  def _update(self, c):
    ret = self.CS.update(self.cp, self.cp_cam)
    self.CS = self.sp_update_params(self.CS)

    buttonEvents = []

    for button in self.CS.buttonStates:
      if self.CS.buttonStates[button] != self.buttonStatesPrev[button]:
        be = car.CarState.ButtonEvent.new_message()
        be.type = button
        be.pressed = self.CS.buttonStates[button]
        buttonEvents.append(be)

    self.CS.mads_enabled = self.get_sp_cruise_main_state(ret, self.CS)

    self.CS.accEnabled, buttonEvents = self.get_sp_v_cruise_non_pcm_state(ret, self.CS.accEnabled,
                                                                          buttonEvents, c.vCruise)

    if ret.cruiseState.available:
      if self.enable_mads:
        if not self.CS.prev_mads_enabled and self.CS.mads_enabled:
          self.CS.madsEnabled = True
        if not self.CS.prev_lkas_enabled and self.CS.lkas_enabled:
          self.CS.madsEnabled = not self.CS.madsEnabled
        self.CS.madsEnabled = self.get_acc_mads(ret.cruiseState.enabled, self.CS.accEnabled, self.CS.madsEnabled)
      ret, self.CS = self.toggle_gac(ret, self.CS, self.CS.buttonStates["gapAdjustCruise"], 1, 3, 4, "-")
    else:
      self.CS.madsEnabled = False

    if not self.CP.pcmCruise or (self.CP.pcmCruise and self.CP.minEnableSpeed > 0):
      if any(b.type == ButtonType.cancel for b in buttonEvents):
        self.CS.madsEnabled, self.CS.accEnabled = self.get_sp_cancel_cruise_state(self.CS.madsEnabled)
    if self.get_sp_pedal_disengage(ret):
      self.CS.madsEnabled, self.CS.accEnabled = self.get_sp_cancel_cruise_state(self.CS.madsEnabled)
      ret.cruiseState.enabled = False if self.CP.pcmCruise else self.CS.accEnabled

    if self.CP.pcmCruise and self.CP.minEnableSpeed > 0 and self.CP.pcmCruiseSpeed:
      if ret.gasPressed and not ret.cruiseState.enabled:
        self.CS.accEnabled = False
      self.CS.accEnabled = ret.cruiseState.enabled or self.CS.accEnabled

    ret, self.CS = self.get_sp_common_state(ret, self.CS)

    if self.CS.out.madsEnabled != self.CS.madsEnabled:
      if self.mads_event_lock:
        buttonEvents.append(create_mads_event(self.mads_event_lock))
        self.mads_event_lock = False
    else:
      if not self.mads_event_lock:
        buttonEvents.append(create_mads_event(self.mads_event_lock))
        self.mads_event_lock = True

    ret.buttonEvents = buttonEvents

    events = self.create_common_events(ret, c, extra_gears=[GearShifter.manumatic], pcm_enable=False)

    events, ret = self.create_sp_events(self.CS, ret, events)

    if not self.CS.vehicle_sensors_valid:
      events.add(car.CarEvent.EventName.vehicleSensorsInvalid)
    if self.CS.hybrid_platform:
      events.add(car.CarEvent.EventName.startupNoControl)

    ret.events = events.to_msg()

    # update previous car states
    self.buttonStatesPrev = self.CS.buttonStates.copy()

    return ret

  def apply(self, c, now_nanos):
    return self.CC.update(c, self.CS, now_nanos)
