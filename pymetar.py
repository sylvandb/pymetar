#!/usr/bin/env python3
# -*- coding: utf8 -*-
# pylint: disable-msg=C0103 # Disable naming style messages
"""
PyMETAR is a python module and command line tool designed to fetch Metar
reports from the NOAA (https://www.noaa.gov) and allow access to the
included weather information.
"""
# pymetar (C) 2022 Sylvan Butler
# Pymetar (c) 2002-2018 Tobias Klausmann
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA."""

import datetime
import re
import requests


__author__ = "sylvan butler based on work by klausman-pymetar@schwarzvogel.de"
__version__ = "2.0"

CLOUD_RE_STR = (r"^(CAVOK|CLR|SKC|BKN|SCT|FEW|OVC|NSC)([0-9]{3})?"
                r"(TCU|CU|CB|SC|CBMAM|ACC|SCSL|CCSL|ACSL)?$")
COND_RE_STR = (r"^[-+]?(VC|MI|BC|PR|TS|BL|SH|DR|FZ)?(DZ|RA|SN|SG|IC|PE|"
               r"GR|GS|UP|BR|FG|FU|VA|SA|HZ|PY|DU|SQ|SS|DS|PO|\+?FC)$")


class EmptyReportException(Exception):
    """This gets thrown when the ReportParser gets fed an empty report"""

class EmptyIDException(Exception):
    """This gets thrown when the ReportFetcher is called with an empty ID"""

class NetworkException(Exception):
    """This gets thrown when a network error occurs"""

class GarbledReportException(Exception):
    """This gets thrown when the report is not valid ASCII or Unicode"""


# What a boring list to type !
#
# It seems the NOAA doesn't want to return plain text, but considering the
# format of their response, this is not to save bandwidth :-)

_WEATHER_CONDITIONS = {
    "DZ": ("Drizzle", "rain", {
           "": "Moderate drizzle",
           "-": "Light drizzle",
           "+": "Heavy drizzle",
           "VC": "Drizzle in the vicinity",
           "MI": "Shallow drizzle",
           "BC": "Patches of drizzle",
           "PR": "Partial drizzle",
           "TS": ("Thunderstorm", "storm"),
           "BL": "Windy drizzle",
           "SH": "Showers",
           "DR": "Drifting drizzle",
           "FZ": "Freezing drizzle",
           }),
    "RA": ("Rain", "rain", {
           "": "Moderate rain",
           "-": "Light rain",
           "+": "Heavy rain",
           "VC": "Rain in the vicinity",
           "MI": "Shallow rain",
           "BC": "Patches of rain",
           "PR": "Partial rainfall",
           "TS": ("Thunderstorm", "storm"),
           "BL": "Blowing rainfall",
           "SH": "Rain showers",
           "DR": "Drifting rain",
           "FZ": "Freezing rain",
           }),
    "SN": ("Snow", "snow", {
           "": "Moderate snow",
           "-": "Light snow",
           "+": "Heavy snow",
           "VC": "Snow in the vicinity",
           "MI": "Shallow snow",
           "BC": "Patches of snow",
           "PR": "Partial snowfall",
           "TS": ("Snowstorm", "storm"),
           "BL": "Blowing snowfall",
           "SH": "Snowfall showers",
           "DR": "Drifting snow",
           "FZ": "Freezing snow",
           }),
    "SG": ("Snow grains", "snow", {
           "": "Moderate snow grains",
           "-": "Light snow grains",
           "+": "Heavy snow grains",
           "VC": "Snow grains in the vicinity",
           "MI": "Shallow snow grains",
           "BC": "Patches of snow grains",
           "PR": "Partial snow grains",
           "TS": ("Snowstorm", "storm"),
           "BL": "Blowing snow grains",
           "SH": "Snow grain showers",
           "DR": "Drifting snow grains",
           "FZ": "Freezing snow grains",
           }),
    "IC": ("Ice crystals", "snow", {
           "": "Moderate ice crystals",
           "-": "Few ice crystals",
           "+": "Heavy ice crystals",
           "VC": "Ice crystals in the vicinity",
           "BC": "Patches of ice crystals",
           "PR": "Partial ice crystals",
           "TS": ("Ice crystal storm", "storm"),
           "BL": "Blowing ice crystals",
           "SH": "Showers of ice crystals",
           "DR": "Drifting ice crystals",
           "FZ": "Freezing ice crystals",
           }),
    "PE": ("Ice pellets", "snow", {
           "": "Moderate ice pellets",
           "-": "Few ice pellets",
           "+": "Heavy ice pellets",
           "VC": "Ice pellets in the vicinity",
           "MI": "Shallow ice pellets",
           "BC": "Patches of ice pellets",
           "PR": "Partial ice pellets",
           "TS": ("Ice pellets storm", "storm"),
           "BL": "Blowing ice pellets",
           "SH": "Showers of ice pellets",
           "DR": "Drifting ice pellets",
           "FZ": "Freezing ice pellets",
           }),
    "GR": ("Hail", "rain", {
           "": "Moderate hail",
           "-": "Light hail",
           "+": "Heavy hail",
           "VC": "Hail in the vicinity",
           "MI": "Shallow hail",
           "BC": "Patches of hail",
           "PR": "Partial hail",
           "TS": ("Hailstorm", "storm"),
           "BL": "Blowing hail",
           "SH": "Hail showers",
           "DR": "Drifting hail",
           "FZ": "Freezing hail",
           }),
    "GS": ("Small hail", "rain", {
           "": "Moderate small hail",
           "-": "Light small hail",
           "+": "Heavy small hail",
           "VC": "Small hail in the vicinity",
           "MI": "Shallow small hail",
           "BC": "Patches of small hail",
           "PR": "Partial small hail",
           "TS": ("Small hailstorm", "storm"),
           "BL": "Blowing small hail",
           "SH": "Showers of small hail",
           "DR": "Drifting small hail",
           "FZ": "Freezing small hail",
           }),
    "UP": ("Precipitation", "rain", {
           "": "Moderate precipitation",
           "-": "Light precipitation",
           "+": "Heavy precipitation",
           "VC": "Precipitation in the vicinity",
           "MI": "Shallow precipitation",
           "BC": "Patches of precipitation",
           "PR": "Partial precipitation",
           "TS": ("Unknown thunderstorm", "storm"),
           "BL": "Blowing precipitation",
           "SH": "Showers, type unknown",
           "DR": "Drifting precipitation",
           "FZ": "Freezing precipitation",
           }),
    "BR": ("Mist", "fog", {
           "": "Moderate mist",
           "-": "Light mist",
           "+": "Thick mist",
           "VC": "Mist in the vicinity",
           "MI": "Shallow mist",
           "BC": "Patches of mist",
           "PR": "Partial mist",
           "BL": "Mist with wind",
           "DR": "Drifting mist",
           "FZ": "Freezing mist",
           }),
    "FG": ("Fog", "fog", {
           "": "Moderate fog",
           "-": "Light fog",
           "+": "Thick fog",
           "VC": "Fog in the vicinity",
           "MI": "Shallow fog",
           "BC": "Patches of fog",
           "PR": "Partial fog",
           "BL": "Fog with wind",
           "DR": "Drifting fog",
           "FZ": "Freezing fog",
           }),
    "FU": ("Smoke", "fog", {
           "": "Moderate smoke",
           "-": "Thin smoke",
           "+": "Thick smoke",
           "VC": "Smoke in the vicinity",
           "MI": "Shallow smoke",
           "BC": "Patches of smoke",
           "PR": "Partial smoke",
           "TS": ("Smoke w/ thunders", "storm"),
           "BL": "Smoke with wind",
           "DR": "Drifting smoke",
           }),
    "VA": ("Volcanic ash", "fog", {
           "": "Moderate volcanic ash",
           "+": "Thick volcanic ash",
           "VC": "Volcanic ash in the vicinity",
           "MI": "Shallow volcanic ash",
           "BC": "Patches of volcanic ash",
           "PR": "Partial volcanic ash",
           "TS": ("Volcanic ash w/ thunders", "storm"),
           "BL": "Blowing volcanic ash",
           "SH": "Showers of volcanic ash",
           "DR": "Drifting volcanic ash",
           "FZ": "Freezing volcanic ash",
           }),
    "SA": ("Sand", "fog", {
           "": "Moderate sand",
           "-": "Light sand",
           "+": "Heavy sand",
           "VC": "Sand in the vicinity",
           "BC": "Patches of sand",
           "PR": "Partial sand",
           "BL": "Blowing sand",
           "DR": "Drifting sand",
           }),
    "HZ": ("Haze", "fog", {
           "": "Moderate haze",
           "-": "Light haze",
           "+": "Thick haze",
           "VC": "Haze in the vicinity",
           "MI": "Shallow haze",
           "BC": "Patches of haze",
           "PR": "Partial haze",
           "BL": "Haze with wind",
           "DR": "Drifting haze",
           "FZ": "Freezing haze",
           }),
    "PY": ("Sprays", "fog", {
           "": "Moderate sprays",
           "-": "Light sprays",
           "+": "Heavy sprays",
           "VC": "Sprays in the vicinity",
           "MI": "Shallow sprays",
           "BC": "Patches of sprays",
           "PR": "Partial sprays",
           "BL": "Blowing sprays",
           "DR": "Drifting sprays",
           "FZ": "Freezing sprays",
           }),
    "DU": ("Dust", "fog", {
           "": "Moderate dust",
           "-": "Light dust",
           "+": "Heavy dust",
           "VC": "Dust in the vicinity",
           "BC": "Patches of dust",
           "PR": "Partial dust",
           "BL": "Blowing dust",
           "DR": "Drifting dust",
           }),
    "SQ": ("Squall", "storm", {
           "": "Moderate squall",
           "-": "Light squall",
           "+": "Heavy squall",
           "VC": "Squall in the vicinity",
           "PR": "Partial squall",
           "TS": "Thunderous squall",
           "BL": "Blowing squall",
           "DR": "Drifting squall",
           "FZ": "Freezing squall",
           }),
    "SS": ("Sandstorm", "fog", {
           "": "Moderate sandstorm",
           "-": "Light sandstorm",
           "+": "Heavy sandstorm",
           "VC": "Sandstorm in the vicinity",
           "MI": "Shallow sandstorm",
           "PR": "Partial sandstorm",
           "TS": ("Thunderous sandstorm", "storm"),
           "BL": "Blowing sandstorm",
           "DR": "Drifting sandstorm",
           "FZ": "Freezing sandstorm",
           }),
    "DS": ("Duststorm", "fog", {
           "": "Moderate duststorm",
           "-": "Light duststorm",
           "+": "Heavy duststorm",
           "VC": "Duststorm in the vicinity",
           "MI": "Shallow duststorm",
           "PR": "Partial duststorm",
           "TS": ("Thunderous duststorm", "storm"),
           "BL": "Blowing duststorm",
           "DR": "Drifting duststorm",
           "FZ": "Freezing duststorm",
           }),
    "PO": ("Dustwhirls", "fog", {
           "": "Moderate dustwhirls",
           "-": "Light dustwhirls",
           "+": "Heavy dustwhirls",
           "VC": "Dustwhirls in the vicinity",
           "MI": "Shallow dustwhirls",
           "BC": "Patches of dustwhirls",
           "PR": "Partial dustwhirls",
           "BL": "Blowing dustwhirls",
           "DR": "Drifting dustwhirls",
           }),
    "+FC": ("Tornado", "storm", {
            "": "Moderate tornado",
            "+": "Raging tornado",
            "VC": "Tornado in the vicinity",
            "PR": "Partial tornado",
            "TS": "Thunderous tornado",
            "BL": "Tornado",
            "DR": "Drifting tornado",
            "FZ": "Freezing tornado",
            }),
    "FC": ("Funnel cloud", "fog", {
           "": "Moderate funnel cloud",
           "-": "Light funnel cloud",
           "+": "Thick funnel cloud",
           "VC": "Funnel cloud in the vicinity",
           "MI": "Shallow funnel cloud",
           "BC": "Patches of funnel cloud",
           "PR": "Partial funnel cloud",
           "BL": "Funnel cloud w/ wind",
           "DR": "Drifting funnel cloud",
           }),
}

CLOUDTYPES = {
    "ACC": "altocumulus castellanus",
    "ACSL": "standing lenticular altocumulus",
    "CB": "cumulonimbus",
    "CBMAM": "cumulonimbus mammatus",
    "CCSL": "standing lenticular cirrocumulus",
    "CU": "cumulus",
    "SCSL": "standing lenticular stratocumulus",
    "SC": "stratocumulus",
    "TCU": "towering cumulus"
}



class WeatherReport:
    """Incorporates both the unparsed textual representation of the
    weather report and the parsed values as soon as they are parsed
    """


    def _clearallfields(self):
        """Clear all fields values."""
        self.parsed = False
        # initialize all
        properties = [
            # set by constructor
            'FullReport', 'ReportURL', 'StationID',
            # set by parser
            'StationName', 'StationCity', 'StationCountry',
            'StationLatitude', 'StationLongitude', 'StationAltitude',
            'Cycle', 'Time', 'Weather', 'Humidity', 'Pixmap',
            'TemperatureCelsius', 'TemperatureFahrenheit',
            'DewPointCelsius', 'DewPointFahrenheit',
            'WindSpeedMilesPerHour', 'WindSpeedKnots',
            'WindDirection', 'WindCompass',
            'VisibilityMiles', 'PressurehPa', 'PressureInHg', 'RawMetarCode',
            'SkyConditions', 'Conditions', 'Cloudinfo', 'Cloudtype',
            # internal use
            '_w_chill', '_w_chillf',
        ]
        for p in properties:
            if hasattr(self, p):
                raise KeyError("Duplicate property: %s" % (p,))
            setattr(self, p, None)
        """ the wind speed in knots """
        """ wind direction in degrees.  """
        """ wind direction as compass direction (e.g. NE or SSE) """
        """ visibility in miles.  """
        """ relative humidity in percent.  """
        """ pressure in hPa.  """
        """ pressure in inches Hg.  """
        """ the encoded weather report.  """
        """ short weather conditions """
        """ sky conditions """
        """ full station name """
        """ city-part of station name """
        """ country-part of station name """
        """
        cycle value.
        The cycle value is not the frequency or delay between
        observations but the "time slot" in which the observation was made.
        There are 24 cycle slots every day which usually last from N:45 to
        N+1:45. The cycle from 23:45 to 0:45 is cycle 0.
        """
        """
        the station's latitude in dd-mm[-ss]D format :
        dd : degrees
        mm : minutes
        ss : seconds
        D : direction (N, S, E, W)
        """
        """
        the station's longitude in dd-mm[-ss]D format :
        dd : degrees
        mm : minutes
        ss : seconds
        D : direction (N, S, E, W)
        """
        """ the station's altitude above the sea in meters.  """
        """ the URL from which the report was fetched.  """
        """
        the time when the observation was made.  Note that this
        is *not* the time when the report was fetched by us
        Format:  YYYY.MM.DD HHMM UTC
        Example: 2002.04.01 1020 UTC
        """
        """ a suggested pixmap name, without extension, depending on current weather.  """
        """ a tuple consisting of the parsed cloud information and a suggest pixmap name """
        """ a tuple consisting of the parsed sky conditions and a suggested pixmap name """
        """ the complete weather report.  """
        """ the temperature in degrees Celsius.  """
        """ the temperature in degrees Fahrenheit.  """
        """ dewpoint in degrees Celsius.  """
        """ dewpoint in degrees Fahrenheit.  """
        """ the wind speed in miles per hour.  """
        """ cloud type information """


    def __init__(self, MetarStationCode=None, url=None, report=None):
        """Clear all fields and fill in wanted station id."""
        self._clearallfields()
        self.StationID = MetarStationCode
        self.ReportURL = url
        self.FullReport = report

    def FetchReport(self):
        if not self.ReportURL or not self.FullReport:
            self.StationID, self.ReportURL, self.FullReport = _fetch(self.StationID)

    def ParseReport(self):
        if not self.parsed:
            self._parse_report()

    @property
    def PressuremmHg(self):
        """ pressure in mmHg.  """
        # 1 in = 25.4 mm => 1 inHg = 25.4 mmHg
        return self.PressureInHg * 25.4000

    @property
    def WindSpeedMPS(self):
        """ the wind speed in meters per second.  """
        if self.WindSpeedMilesPerHour is not None:
            return self.WindSpeedMilesPerHour * 0.44704

    @property
    def WindSpeedBeaufort(self):
        """
        the wind speed in the Beaufort scale
        cf. https://en.wikipedia.org/wiki/Beaufort_scale
        """
        w = self.WindSpeedMPS
        if w is not None:
            return round((w / 0.8359648) ** (2 / 3.0))

    @property
    def VisibilityKilometers(self):
        """ visibility in km.  """
        if self.VisibilityMiles is not None:
            return self.VisibilityMiles * 1.609344

    @property
    def StationPosition(self):
        """
        latitude, longitude and altitude above sea level of station
        as a tuple. Some stations don't deliver altitude, for those, None
        is returned as altitude.  The lat/longs are expressed as follows:
        xx-yyd
        where xx is degrees, yy minutes and d the direction.
        Thus 51-14N means 51 degrees, 14 minutes north.  d may take the
        values N, S for latitues and W, E for longitudes. Latitude and
        Longitude may include seconds.  Altitude is always given as meters
        above sea level, including a trailing M.
        Schipohl Int. Airport Amsterdam has, for example:
        ('52-18N', '004-46E', '-2M')
        Moenchengladbach (where I live):
        ('51-14N', '063-03E', None)
        If you need lat and long as float values, look at
        StationPositionFloat instead
        """
        # convert self.StationAltitude to string for consistency
        return (self.StationLatitude, self.StationLongitude, str(self.StationAltitude))

    @property
    def StationPositionFloat(self):
        """
        latitude and longitude as float values in a
        tuple (lat, long, alt).
        """
        return (self.StationLatitudeFloat, self.StationLongitudeFloat, self.StationAltitude)

    @property
    def StationLatitudeFloat(self):
        """ latitude as a float """
        return self._parse_lat_long(self.StationLatitude)

    @property
    def StationLongitudeFloat(self):
        """ Longitude as a float """
        return self._parse_lat_long(self.StationLongitude)

    @property
    def ISOTime(self):
        """
        the time when the observation was made in ISO 8601 format
        (e.g. 2002-07-25 15:12:00Z)
        """
        return self._metar_to_iso8601(self.Time)

    @property
    def ApparentTemperatureCelsius(self):
        """ australian apparent temperature aka heat index, cf. wind chill reference """
        C = self.TemperatureCelsius
        mps = self.WindSpeedMPS
        rh = self.Humidity
        if C is not None and mps is not None and rh is not None:
            e = rh / 100 * 6.105 * 2.71828 ** ((17.27 * C) / (237.7 + C))
            return C + 0.33 * e - 0.7 * mps - 4.0

    @property
    def ApparentTemperatureFahrenheit(self):
        C = self.ApparentTemperatureCelsius
        if C is not None:
            return C * 1.8 + 32

    @property
    def WindchillCelsius(self):
        """
        wind chill in degrees Celsius
        cf. https://en.wikipedia.org/wiki/Wind_chill - North American wind chill index
        """
        return self._calc_w_chill() if self._w_chill is None else self._w_chill

    @property
    def WindchillFahrenheit(self):
        """ wind chill in degrees Fahrenheit """
        return self._calc_w_chillf() if self._w_chillf is None else self._w_chillf


    def _calc_w_chill(self):
        C = self.TemperatureCelsius
        ws = self.WindSpeedMPS
        kph = (ws or 0) * 3.6
        if C is not None and ws is not None and C <= 10 and kph > 4.8:
            self._w_chill = (13.12 + 0.6215 * C -
                            11.37 * kph ** 0.16 +
                            0.3965 * C * kph ** 0.16)
        else:
            self._w_chill = C
        return self._w_chill


    def _calc_w_chillf(self):
        F = self.TemperatureFahrenheit
        ws = self.WindSpeedMilesPerHour
        mph = ws or 0
        if F is not None and ws is not None and F <= 50 and mph > 3:
            self._w_chillf = (35.74 + 0.6215 * F -
                             35.75 * mph ** 0.16 +
                             0.4275 * F * mph ** 0.16)
        else:
            self._w_chillf = F
        return self._w_chillf


    def _extractCloudInformation(self):
        """
        Extract cloud information. Return None or a tuple (sky type as a
        string of text, cloud type (if any)  and suggested pixmap name)
        """
        matches = self._match_WeatherPart(CLOUD_RE_STR)
        skytype = None
        ctype = None
        pixmap = None
        for wcloud in matches:
            if wcloud is not None:
                stype = wcloud[:3]
                if stype in ("CLR", "SKC", "CAV", "NSC"):
                    skytype = "Clear sky"
                    pixmap = "sun"
                elif stype == "BKN":
                    skytype = "Broken clouds"
                    pixmap = "suncloud"
                elif stype == "SCT":
                    skytype = "Scattered clouds"
                    pixmap = "suncloud"
                elif stype == "FEW":
                    skytype = "Few clouds"
                    pixmap = "suncloud"
                elif stype == "OVC":
                    skytype = "Overcast"
                    pixmap = "cloud"
                if ctype is None:
                    ctype = CLOUDTYPES.get(wcloud[6:], None)

        return (skytype, ctype, pixmap)


    def _extractSkyConditions(self):
        """
        Extract sky condition information from the encoded report. Return
        a tuple containing the description of the sky conditions as a
        string and a suggested pixmap name for an icon representing said
        sky condition.
        """
        matches = self._match_WeatherPart(COND_RE_STR)
        for wcond in matches:
            if len(wcond) > 3 and wcond.startswith(('+', '-')):
                wcond = wcond[1:]

            if wcond.startswith(('+', '-')):
                pphen = 1
            elif len(wcond) < 4:
                pphen = 0
            else:
                pphen = 2
            squal = wcond[:pphen]
            sphen = wcond[pphen: pphen + 4]
            phenomenon = _WEATHER_CONDITIONS.get(sphen, None)
            if phenomenon is not None:
                (name, pixmap, phenomenon) = phenomenon
                pheninfo = phenomenon.get(squal, name)
                if not isinstance(pheninfo, type(())):
                    return (pheninfo, pixmap)
                else:
                    # contains pixmap info
                    return pheninfo


    def _match_WeatherPart(self, regexp):
        """
        Return the matching part of the encoded Metar report.
        regexp: the regexp needed to extract this part.
        Return the first matching string or None.
        WARNING: Some Metar reports may contain several matching
        strings, only the first one is taken into account!
        """
        matches = []
        if self.RawMetarCode is not None:
            myre = re.compile(regexp)
            for wpart in self.RawMetarCode.split():
                match = myre.match(wpart)
                if match:
                    matches.append(match.group())
        return matches


    @staticmethod
    def _metar_to_iso8601(metardate):
        """Convert a metar date to an ISO8601 date."""
        if metardate:
            (date, hour) = metardate.split()[:2]
            (year, month, day) = date.split('.')
            # assuming tz is always 'UTC', aka 'Z'
            return ("%s-%s-%s %s:%s:00Z" %
                    (year, month, day, hour[:2], hour[2:4]))


    @staticmethod
    def _parse_lat_long(latlong):
        """
        Parse Lat or Long in METAR notation into float values. N and E
        are +, S and W are -. Expects one positional string and returns
        one float value.
        """
        # I know, I could invert this if and put
        # the rest of the function into its block,
        # but I find it to be more readable this way
        if not latlong:
            return None

        cap_inp = latlong.upper().strip()
        elements = cap_inp.split('-')
        # Extract N/S/E/W
        compass_dir = elements[-1][-1]
        # get rid of compass direction
        elements[-1] = elements[-1][:-1]
        elen = len(elements)
        coords = float(elements[0])
        if elen > 1:
            coords += float(elements[1]) / 60.0
            if elen > 2:
                coords += float(elements[2]) / 3600.0
        return -coords if compass_dir in 'WS' else coords


    def _parse_report(self):
        """Parse raw METAR data from a WeatherReport object into actual values"""
        if self.FullReport is None:
            raise EmptyReportException(
                "No report given")

        try:
            lines = self.FullReport.split("\n")
        except (TypeError, UnicodeDecodeError):
            raise GarbledReportException(
                "Report is not valid text.")

        for line in lines:
            try:
                header, data = line.split(":", 1)
            except ValueError:
                header = data = line

            header = header.strip()
            data = data.strip()

            # The station id inside the report
            # As the station line may contain additional sets of (),
            # we have to search from the rear end and flip things around
            if header.find("(" + self.StationID + ")") != -1:
                id_offset = header.find("(" + self.StationID + ")")
                loc = data[:id_offset]
                coords = data[id_offset:]
                try:
                    loc = loc.strip()
                    rloc = loc[::-1]
                    rcoun, rcity = rloc.split(",", 1)
                except ValueError:
                    rcity = ""
                    rcoun = ""
                    coords = data
                lat, lng, alt = coords.split()[1:4]
                # A few jokers out there think O==0
                lat = lat.replace("O", "0")
                lng = lng.replace("O", "0")
                alt = alt.replace("O", "0")
                try:
                    alt = int(alt[:-1])  # cut off 'M' for meters
                except ValueError:
                    alt = None

                self.StationCity = rcity.strip()[::-1]
                self.StationCountry = rcoun.strip()[::-1]
                self.StationName = loc
                self.StationLatitude = lat
                self.StationLongitude = lng
                self.StationAltitude = alt

            # The line containing date and time of the report
            # We have to make sure that the station ID is *not*
            # in this line to avoid trying to parse the ob: line
            elif " UTC" in data and self.StationID not in data:
                rtime = data.split("/")[1]
                self.Time = rtime.strip()

            # temperature
            elif header == "Temperature":
                fnht, cels = data.split(None, 3)[0:3:2]
                self.TemperatureFahrenheit = float(fnht)
                # The string we have split is "(NN C)", hence the slice
                self.TemperatureCelsius = float(cels[1:])

            # wind chill
            elif header == "Windchill":
                fnht, cels = data.split(None, 3)[0:3:2]
                self._w_chillf = float(fnht)
                # The string we have split is "(NN C)", hence the slice
                self._w_chill = float(cels[1:])

            # wind dir and speed
            elif header == "Wind":
                if "Calm" in data:
                    self.WindSpeedKnots = 0.0
                    self.WindSpeedMilesPerHour = 0.0
                    self.WindDirection = None
                    self.WindCompass = None
                elif "Variable" in data:
                    speed = data.split(" ", 3)[2]
                    self.WindSpeedKnots = int(data.split(" ", 5)[4][1:])
                    self.WindSpeedMilesPerHour = int(speed)
                    self.WindDirection = None
                    self.WindCompass = None
                else:
                    fields = data.split(" ", 9)[0:9]
                    comp = fields[2]
                    deg = fields[3]
                    speed = fields[6]
                    speedkt = fields[8][1:]
                    self.WindDirection = int(deg[1:])
                    self.WindCompass = comp.strip()
                    self.WindSpeedKnots = int(speedkt)
                    self.WindSpeedMilesPerHour = int(speed)

            # visibility
            elif header == "Visibility":
                for visgroup in data.split():
                    try:
                        self.VisibilityMiles = float(visgroup)
                        break
                    except ValueError:
                        break

            # dew point
            elif header == "Dew Point":
                fnht, cels = data.split(None, 3)[0:3:2]
                self.DewPointFahrenheit = float(fnht)
                # The string we have split is "(NN C)", hence the slice
                self.DewPointCelsius = float(cels[1:])

            # humidity
            elif header == "Relative Humidity":
                h = data.split("%", 1)[0]
                self.Humidity = int(h)

            # pressure
            elif header == "Pressure (altimeter)":
                press = data.split()
                self.PressureInHg = float(press[0])
                self.PressurehPa = float(press[-2][1:])

            # short weather desc. ("rain", "mist", ...)
            elif header == "Weather":
                self.Weather = data

            # short desc. of sky conditions
            elif header == "Sky conditions":
                self.SkyConditions = data

            # the encoded report itself
            elif header == "ob":
                self.RawMetarCode = data.strip()

            # the cycle value ("time slot")
            elif header == "cycle":
                try:
                    self.Cycle = int(data)
                except ValueError:
                    # cycle value is missing or garbled, assume cycle 0
                    # TODO: parse the date/time header if it isn't too involved
                    self.Cycle = 0

        # cloud info
        cloudinfo = self._extractCloudInformation()
        (cloudinfo, cloudtype, cloudpixmap) = cloudinfo

        # Cloud type (Cumulonimbus etc.)
        if self.Cloudtype is None:
            self.Cloudtype = cloudtype

        conditions = self._extractSkyConditions()
        if conditions is not None:
            (conditions, condpixmap) = conditions
        else:
            (conditions, condpixmap) = (None, None)

        # Some people might want to always use sky or cloud info specifially
        self.Cloudinfo = (cloudinfo, cloudpixmap)
        self.Conditions = (conditions, condpixmap)

        # fill the weather information
        self.Weather = self.Weather or conditions or cloudinfo

        # Pixmap guessed from general conditions has priority
        # over pixmap guessed from clouds
        self.Pixmap = condpixmap or cloudpixmap

        # report is complete
        self.parsed = 1



def MakeReport(self, StationCode, RawReport):
    """
    Take a string (RawReport) and a station code and turn it
    into an object suitable for ReportParser
    """
    stationid = StationCode.upper()
    reporturl = "%s%s.TXT" % (baseurl, stationid)
    return WeatherReport(stationid, url=reporturl, report=RawReport)


def FetchReport(StationCode, proxy=None, baseurl=None):
    """Fetches a report from a given METAR id, optionally taking into
       account a different baseurl and using environment var-specified
       If proxy is not None, a proxy URL of the form
          protocol://user:password@host.name.tld:port/
       is expected, for example:
          http://squid.somenet.com:3128/
    """

    if StationCode is None:
        raise EmptyIDException("No ID given")
    stationid, url, report = _fetch(StationCode, baseurl=baseurl, proxy=proxy)
    return WeatherReport(stationid, url=url, report=report)


def _fetch(stationid, proxy=None, baseurl=None):
    baseurl = baseurl or "https://tgftp.nws.noaa.gov/data/observations/metar/decoded/"
    stationid = stationid.upper()
    reporturl = "%s%s.TXT" % (baseurl, stationid)
    rep = _cache(stationid)
    if rep:
        return stationid, reporturl, rep
    if proxy:
        fn = requests.get(reporturl, proxies={'http': proxy, 'https': proxy})
    else:
        fn = requests.get(reporturl)
    if fn.status_code != 200:
        raise NetworkException(
            "Could not fetch METAR report: %s" % (fn.status_code))
    rep = fn.text.strip()
    _cache(stationid, rep)
    return stationid, reporturl, rep

def _cache(stationid, report=None):
    cache = '/tmp/%s.TXT' % (stationid,)
    # save a report
    if report:
        with open(cache, 'w') as f:
            f.write(report)
        return
    # load a cached report
    try:
        with open(cache, 'r') as f:
            rep = f.read()
    except OSError:
        pass
    else:
        lines = iter(rep.split('\n'))
        l = next(lines)
        l = next(lines)
        metardate = l.split("/")[1].strip()
        repdate = _metar_to_date(metardate)
        # return the cache version if recent enough (1hr5min)
        if (datetime.datetime.now(datetime.timezone.utc) - repdate).total_seconds() < 3900:
            return rep + '\ncache: ' + cache

def _metar_to_date(metardate):
    """Convert a metar date to a python datetime."""
    if metardate:
        (date, hour) = metardate.split()[:2]
        (year, month, day) = date.split('.')
        # assuming tz is always 'UTC', aka 'Z'
        return datetime.datetime.fromisoformat("%s-%s-%s %s:%s:00+00:00" %
                (year, month, day, hour[:2], hour[2:4]))




if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2 or sys.argv[1] == "--help":
        print("Usage: %s <station id>\n" % sys.argv[0], file=sys.stderr)
        print("Station IDs can be found at: https://www.aviationweather.gov/metar\n", file=sys.stderr)
        sys.exit(1)

    elif (sys.argv[1] == "--version"):
        print("%s pymetar lib v%s" % (sys.argv[0], __version__))
        sys.exit(0)

    try:
        wr = FetchReport(sys.argv[1])
    except Exception as e:
        print(
            "Something went wrong when fetching the report.\n"
            "These usually are transient problems if the station "
            "ID is valid. \nThe error encountered was:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)

    wr.ParseReport()

    print("\n-------- Full Report --------\n%s" % (wr.FullReport,))
    print("\n-------- Properties --------")
    for k, v in ((k, getattr(wr, k)) for k in dir(wr)):
        if k != "FullReport" and k[0] != '_' and not callable(v):
            print("%s: %s" % (k, v))
    print("\n------ End ------")
