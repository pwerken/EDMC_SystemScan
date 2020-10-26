# SystemScan plugin for [EDMC](https://github.com/Marginal/EDMarketConnector/wiki)

Plugin for [EDMC](https://github.com/EDCD/EDMarketConnector/wiki) that helps
me with my completionist/OCD of wanting to FSS scan every system I visit.

Additionally it also lists the bodies that are worth mapping, ie ammonia-,
water-, and earth-like world and the terraformable worlds.

## Installation

 1. Clone this repository or download and extract the [repository zip archive](https://github.com/pwerken/EDMC_SystemScan/archive/main.zip)
	in your EDMC plugin directory.
 2. Then (re)start EDMC.

## Usage

When entering the system a plugin will display a red 'Discovery Scan' notice.
After honking it will show a orange 'Full Spectrum Scan'. When that is also
completed the interesting bodies will be listed.

If you've already visited the system before and scanned it completely, the FSS
step will be skipped.  In this case the will be no journal events for
populating the interesting bodies listing.

To work around this the plugin always asks [EDSM](https://www.edsm.net/) for
the bodies on entering a system.
