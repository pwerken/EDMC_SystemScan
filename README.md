# SystemScan plugin for [EDMC](https://github.com/Marginal/EDMarketConnector/wiki)

Plugin for [EDMC](https://github.com/EDCD/EDMarketConnector/wiki) that helps
me with my completionist/OCD of wanting to FSS scan every system I visit.

Additionally it lists the bodies that are worth mapping:
ammonia, water and earth-like worlds.

## Installation

 1. Clone this repository *or* download and extract the
    [repository zip archive](https://github.com/pwerken/EDMC_SystemScan/archive/main.zip)
    in your EDMC plugin directory.
 2. Then (re)start EDMC.

## Usage

When entering the system this plugin will display a red 'Discovery Scan'
notice.

![discovery scan](/preview/discoveryscan.png)

After honking it will change to an orange 'Full Spectrum Scan'.
This also shows your progress in scanning the system.

![discovery scan](/preview/fullspectrumscan.png)

When completed the interesting bodies will be listed.

![discovery scan](/preview/systemscancomplete.png)

On entering a system this plugin also queries [Spansh](https://www.spansh.co.uk)
for all the bodies.  This populates the interesting bodies listed in the
case where the 'Discovery Scan' reports that FSS is already complete.
