#!/usr/bin/env python3
# -*- coding: iso-8859-15 -*-

__version__ = "2.1"

import pymetar
import sys

print("pymet v%s using pymetar lib v%s" % (__version__, pymetar.__version__))

if len(sys.argv) < 2:
    station = "NZCM"
else:
    station = sys.argv[1]

pr = pymetar.FetchReport(station)

print("\n--------- Full report ---------")
print(pr.FullReport)
print("------- End full report -------")

pr.ParseReport()

print("\n-------- Properties --------")
for k, v in ((k, getattr(pr, k)) for k in dir(pr)):
    if k != "FullReport" and k[0] != '_' and not callable(v):
        print("%s: %s" % (k, v))
print("------ End Properties ------")

print("\n----- Report Primary Values -----")
print("TemperatureCelsius: %s" % (pr.TemperatureCelsius,))
print("TemperatureFahrenheit: %s" % (pr.TemperatureFahrenheit,))
print("DewPointCelsius: %s" % (pr.DewPointCelsius,))
print("DewPointFahrenheit: %s" % (pr.DewPointFahrenheit,))
print("WindSpeed: %s" % (pr.WindSpeed,))
print("WindSpeedMilesPerHour: %s" % (pr.WindSpeedMilesPerHour,))
print("WindDirection: %s" % (pr.WindDirection,))
print("WindCompass: %s" % (pr.WindCompass,))
print("VisibilityKilometers: %s" % (pr.VisibilityKilometers,))
print("VisibilityMiles: %s" % (pr.VisibilityMiles,))
print("Humidity: %s" % (pr.Humidity,))
print("Pressure: %s" % (pr.Pressure,))
print("RawMetarCode: %s" % (pr.RawMetarCode,))
print("Weather: %s" % (pr.Weather,))
print("SkyConditions: %s" % (pr.SkyConditions,))
print("StationName: %s" % (pr.StationName,))
print("StationCity: %s" % (pr.StationCity,))
print("StationCountry: %s" % (pr.StationCountry,))
print("Cycle: %s" % (pr.Cycle,))
print("StationPosition: %r" % (pr.StationPosition,))
print("StationPositionFloat: %r" % (pr.StationPositionFloat,))
print("StationLatitude: %s" % (pr.StationLatitude,))
print("StationLatitudeFloat: %s" % (pr.StationLatitudeFloat,))
print("StationLongitude: %s" % (pr.StationLongitude,))
print("StationLongitudeFloat: %s" % (pr.StationLongitudeFloat,))
print("StationAltitude: %s" % (pr.StationAltitude,))
print("ReportURL: %s" % (pr.ReportURL,))
print("Time: %s" % (pr.Time,))
print("ISOTime: %s" % (pr.ISOTime,))
print("Pixmap: %s" % (pr.Pixmap,))
print("Cloudtype: %s" % (pr.Cloudtype,))
print("Windchill: %s" % (pr.Windchill,))
print("WindchillF: %s" % (pr.WindchillF,))
print("ApparentTemperature: %s" % (pr.ApparentTemperature,))
print("ApparentTemperatureF: %s" % (pr.ApparentTemperatureF,))
print("Cloudinfo: %r" % (pr.Cloudinfo,))
print("Conditions: %r" % (pr.Conditions,))

print("--- End Report Primary Values ---")
