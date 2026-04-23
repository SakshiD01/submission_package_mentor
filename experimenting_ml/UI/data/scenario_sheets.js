/**
 * Scenario-first UI payload derived from `scenario_mapping.xlsx`.
 * Auto-filtered: includes ONLY rows where Change column indicates change.
 */

export const SCENARIO_FAMILIES = [
  {
    "id": "direct_route",
    "title": "Scenario 1 \u2014 Shift to Direct Sea Routes",
    "description": "Evaluate freight movement changes when Landbridge traffic is partially replaced by direct Ireland-EU routes after Brexit frictions.",
    "levels": [
      {
        "id": "as_is",
        "label": "Pre-Brexit baseline"
      },
      {
        "id": "scenario_1",
        "label": "Scenario 1"
      },
      {
        "id": "scenario_2",
        "label": "Scenario 2"
      }
    ],
    "parameters": [
      {
        "key": "PerGreenTrucksAPImIR",
        "label": "PerGreenTrucksAPImIR",
        "description": "Percentage of intbound trucks directed to green route at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.2,
          "scenario_2": 0.2
        }
      },
      {
        "key": "DocChkTimeAPImIR",
        "label": "DocChkTimeAPImIR",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAPImIR",
        "label": "PerFullIdnChkAPImIR",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "IdnChkTimeAPImIR",
        "label": "IdnChkTimeAPImIR",
        "description": "Timing of full identity checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 30.0,
          "scenario_2": 30.0
        }
      },
      {
        "key": "PerPhyChkAPImIR",
        "label": "PerPhyChkAPImIR",
        "description": "Percentage of inbound trucks need physical checks (red routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.3,
          "scenario_2": 0.3
        }
      },
      {
        "key": "PhyChkTimeAPImIR",
        "label": "PhyChkTimeAPImIR",
        "description": "Timing of physical checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerSecurityChkAPIR",
        "label": "PerSecurityChkAPIR",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checks at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAPImIR",
        "label": "SecChkTimeAPImIR",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksAgriImIR",
        "label": "PerGreenTrucksAgriImIR",
        "description": "Percentage of Agri-food intbound trucks directed to green route at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocChkTimeAgriImIR",
        "label": "DocChkTimeAgriImIR",
        "description": "Timing of documentary and sealed identity checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAgriImIR",
        "label": "PerFullIdnChkAgriImIR",
        "description": "Percentage of Agri-food inbound trucks need full identity checks (orange routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnChkTimeAgriImIR",
        "label": "IdnChkTimeAgriImIR",
        "description": "Timing of full identity checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkAgriImIR",
        "label": "PerPhyChkAgriImIR",
        "description": "Percentage of Agri-food inbound trucks need physical checks (red routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyChkTimeAgriImIR",
        "label": "PhyChkTimeAgriImIR",
        "description": "Timing of physical checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkAgriIR",
        "label": "PerSecurityChkAgriIR",
        "description": "Percentage of Agri-food inbound trucks for security, license compliance and immegration checks at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAgriImIR",
        "label": "SecChkTimeAgriImIR",
        "description": "Timing of the security, license compliance and immegration checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksAPImUK-W",
        "label": "PerGreenTrucksAPImUK-W",
        "description": "Percentage of intbound trucks directed to green route at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.2,
          "scenario_2": 0.2
        }
      },
      {
        "key": "DocChkTimeAPImUK-W",
        "label": "DocChkTimeAPImUK-W",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAPImUK-W",
        "label": "PerFullIdnChkAPImUK-W",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "IdnChkTimeAPImUK-W",
        "label": "IdnChkTimeAPImUK-W",
        "description": "Timing of full identity checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 30.0,
          "scenario_2": 30.0
        }
      },
      {
        "key": "PerPhyChkAPImUK-W",
        "label": "PerPhyChkAPImUK-W",
        "description": "Percentage of inbound trucks need physical checks (red routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.3,
          "scenario_2": 0.3
        }
      },
      {
        "key": "PhyChkTimeAPImUK-W",
        "label": "PhyChkTimeAPImUK-W",
        "description": "Timing of physical checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerSecurityChkAPUK-W",
        "label": "PerSecurityChkAPUK-W",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checks at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAPUK-W",
        "label": "SecChkTimeAPUK-W",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksAgriImUK-W",
        "label": "PerGreenTrucksAgriImUK-W",
        "description": "Percentage of Agri-food intbound trucks directed to green route at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocChkTimeAgriImUK-W",
        "label": "DocChkTimeAgriImUK-W",
        "description": "Timing of documentary and sealed identity checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAgriImUK-W",
        "label": "PerFullIdnChkAgriImUK-W",
        "description": "Percentage of Agri-food inbound trucks need full identity checks (orange routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnChkTimeAgriImUK-W",
        "label": "IdnChkTimeAgriImUK-W",
        "description": "Timing of full identity checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkAgriImUK-W",
        "label": "PerPhyChkAgriImUK-W",
        "description": "Percentage of Agri-food inbound trucks need physical checks (red routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyChkTimeAgriImUK-W",
        "label": "PhyChkTimeAgriImUK-W",
        "description": "Timing of physical checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkAgriUK-W",
        "label": "PerSecurityChkAgriUK-W",
        "description": "Percentage of Agri-food inbound trucks for security, license compliance and immegration checks at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAgriImUK-W",
        "label": "SecChkTimeAgriImUK-W",
        "description": "Timing of the security, license compliance and immegration checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksImUK-E",
        "label": "PerGreenTrucksImUK-E",
        "description": "Percentage of intbound trucks directed to green route at East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocCheckTimeImUK-E",
        "label": "DocCheckTimeImUK-E",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at East UK Port (Dover)(minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkImUK-E",
        "label": "PerFullIdnChkImUK-E",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnCheckTimeImUK-E",
        "label": "IdnCheckTimeImUK-E",
        "description": "Timing of full identity checks on inbound trucks at East UK Port (Dover) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkImUK-E",
        "label": "PerPhyChkImUK-E",
        "description": "Percentage of inbound trucks need physical checks (red routed) at East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyCheckTimeImUK-E",
        "label": "PhyCheckTimeImUK-E",
        "description": "Timing of physical checks on inbound trucks at East UK Port (Dover) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkUK-E",
        "label": "PerSecurityChkUK-E",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checksat East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecCheckTimeUK-E",
        "label": "SecCheckTimeUK-E",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at East UK Port (Dover) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksImEU",
        "label": "PerGreenTrucksImEU",
        "description": "Percentage of intbound trucks directed to green route at at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocCheckTimeImEU",
        "label": "DocCheckTimeImEU",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkImEU",
        "label": "PerFullIdnChkImEU",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnCheckTimeImEU",
        "label": "IdnCheckTimeImEU",
        "description": "Timing of full identity checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkImEU",
        "label": "PerPhyChkImEU",
        "description": "Percentage of inbound trucks need physical checks (red routed) at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyCheckTimeImEU",
        "label": "PhyCheckTimeImEU",
        "description": "Timing of physical checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkEU",
        "label": "PerSecurityChkEU",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checksat at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecCheckTimeEU",
        "label": "SecCheckTimeEU",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "NumCustomOfficerD",
        "label": "NumCustomOfficerD",
        "description": "Number of custom officers at Dublin port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 4.0,
          "scenario_2": 4.0
        }
      },
      {
        "key": "NumSPSUnitOfficerD",
        "label": "NumSPSUnitOfficerD",
        "description": "Number of SPS officer at Dublin port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "NumCustomOfficerR",
        "label": "NumCustomOfficerR",
        "description": "Number of custom officers at Rosslare port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 4.0,
          "scenario_2": 4.0
        }
      },
      {
        "key": "NumSPSUnitOfficerR",
        "label": "NumSPSUnitOfficerR",
        "description": "Number of SPS officer at Rosslare port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "NumTractorR",
        "label": "NumTractorR",
        "description": "Number of security and document copmpliance officers at Rosslare port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "PerUKTrucksMoveD",
        "label": "PerUKTrucksMoveD",
        "description": "Percentage of outbound trucks from Dublin port to the UK market",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.6,
          "scenario_1": 0.3,
          "scenario_2": 0.1
        }
      },
      {
        "key": "PerLBTrucksMoveD",
        "label": "PerLBTrucksMoveD",
        "description": "Percentage of outbound trucks from Dublin port to the EU-26 market",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.4,
          "scenario_1": 0.7,
          "scenario_2": 0.9
        }
      },
      {
        "key": "DocCheckCost",
        "label": "DocCheckCost",
        "description": "Offical documentary check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 50.0,
          "scenario_2": 50.0
        }
      },
      {
        "key": "IdnCheckCost",
        "label": "IdnCheckCost",
        "description": "Offical full identity check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 100.0,
          "scenario_2": 100.0
        }
      },
      {
        "key": "PhyCheckCost",
        "label": "PhyCheckCost",
        "description": "Offical physical check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 500.0,
          "scenario_2": 500.0
        }
      },
      {
        "key": "SecurityCheckCost",
        "label": "SecurityCheckCost",
        "description": "Offical security check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 500.0,
          "scenario_2": 500.0
        }
      },
      {
        "key": "Name",
        "label": "Name",
        "description": "Description",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      }
    ]
  },
  {
    "id": "non_tariff",
    "title": "Scenario 2 \u2014 Non-Tariff Barrier Operational Efficiency",
    "description": "Assess outcomes when customs, documentary, and physical check operations are improved under post-Brexit non-tariff barriers.",
    "levels": [
      {
        "id": "as_is",
        "label": "Pre-Brexit baseline"
      },
      {
        "id": "scenario_1",
        "label": "Scenario 1"
      },
      {
        "id": "scenario_2",
        "label": "Scenario 2"
      }
    ],
    "parameters": [
      {
        "key": "PerGreenTrucksAPImIR",
        "label": "PerGreenTrucksAPImIR",
        "description": "Percentage of intbound trucks directed to green route at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.2,
          "scenario_2": 0.2
        }
      },
      {
        "key": "DocChkTimeAPImIR",
        "label": "DocChkTimeAPImIR",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAPImIR",
        "label": "PerFullIdnChkAPImIR",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "IdnChkTimeAPImIR",
        "label": "IdnChkTimeAPImIR",
        "description": "Timing of full identity checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 30.0,
          "scenario_2": 30.0
        }
      },
      {
        "key": "PerPhyChkAPImIR",
        "label": "PerPhyChkAPImIR",
        "description": "Percentage of inbound trucks need physical checks (red routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.3,
          "scenario_2": 0.3
        }
      },
      {
        "key": "PhyChkTimeAPImIR",
        "label": "PhyChkTimeAPImIR",
        "description": "Timing of physical checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerSecurityChkAPIR",
        "label": "PerSecurityChkAPIR",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checks at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAPImIR",
        "label": "SecChkTimeAPImIR",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksAgriImIR",
        "label": "PerGreenTrucksAgriImIR",
        "description": "Percentage of Agri-food intbound trucks directed to green route at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocChkTimeAgriImIR",
        "label": "DocChkTimeAgriImIR",
        "description": "Timing of documentary and sealed identity checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAgriImIR",
        "label": "PerFullIdnChkAgriImIR",
        "description": "Percentage of Agri-food inbound trucks need full identity checks (orange routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnChkTimeAgriImIR",
        "label": "IdnChkTimeAgriImIR",
        "description": "Timing of full identity checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkAgriImIR",
        "label": "PerPhyChkAgriImIR",
        "description": "Percentage of Agri-food inbound trucks need physical checks (red routed) at Irish Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyChkTimeAgriImIR",
        "label": "PhyChkTimeAgriImIR",
        "description": "Timing of physical checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkAgriIR",
        "label": "PerSecurityChkAgriIR",
        "description": "Percentage of Agri-food inbound trucks for security, license compliance and immegration checks at Irish Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAgriImIR",
        "label": "SecChkTimeAgriImIR",
        "description": "Timing of the security, license compliance and immegration checks on Agri-food inbound trucks at Irish ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksAPImUK-W",
        "label": "PerGreenTrucksAPImUK-W",
        "description": "Percentage of intbound trucks directed to green route at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.2,
          "scenario_2": 0.2
        }
      },
      {
        "key": "DocChkTimeAPImUK-W",
        "label": "DocChkTimeAPImUK-W",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAPImUK-W",
        "label": "PerFullIdnChkAPImUK-W",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "IdnChkTimeAPImUK-W",
        "label": "IdnChkTimeAPImUK-W",
        "description": "Timing of full identity checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 30.0,
          "scenario_2": 30.0
        }
      },
      {
        "key": "PerPhyChkAPImUK-W",
        "label": "PerPhyChkAPImUK-W",
        "description": "Percentage of inbound trucks need physical checks (red routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.3,
          "scenario_2": 0.3
        }
      },
      {
        "key": "PhyChkTimeAPImUK-W",
        "label": "PhyChkTimeAPImUK-W",
        "description": "Timing of physical checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerSecurityChkAPUK-W",
        "label": "PerSecurityChkAPUK-W",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checks at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAPUK-W",
        "label": "SecChkTimeAPUK-W",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksAgriImUK-W",
        "label": "PerGreenTrucksAgriImUK-W",
        "description": "Percentage of Agri-food intbound trucks directed to green route at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocChkTimeAgriImUK-W",
        "label": "DocChkTimeAgriImUK-W",
        "description": "Timing of documentary and sealed identity checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkAgriImUK-W",
        "label": "PerFullIdnChkAgriImUK-W",
        "description": "Percentage of Agri-food inbound trucks need full identity checks (orange routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnChkTimeAgriImUK-W",
        "label": "IdnChkTimeAgriImUK-W",
        "description": "Timing of full identity checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkAgriImUK-W",
        "label": "PerPhyChkAgriImUK-W",
        "description": "Percentage of Agri-food inbound trucks need physical checks (red routed) at west UK Ports (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyChkTimeAgriImUK-W",
        "label": "PhyChkTimeAgriImUK-W",
        "description": "Timing of physical checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkAgriUK-W",
        "label": "PerSecurityChkAgriUK-W",
        "description": "Percentage of Agri-food inbound trucks for security, license compliance and immegration checks at west UK Ports (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecChkTimeAgriImUK-W",
        "label": "SecChkTimeAgriImUK-W",
        "description": "Timing of the security, license compliance and immegration checks on Agri-food inbound trucks at west UK Ports (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksImUK-E",
        "label": "PerGreenTrucksImUK-E",
        "description": "Percentage of intbound trucks directed to green route at East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocCheckTimeImUK-E",
        "label": "DocCheckTimeImUK-E",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at East UK Port (Dover)(minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkImUK-E",
        "label": "PerFullIdnChkImUK-E",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnCheckTimeImUK-E",
        "label": "IdnCheckTimeImUK-E",
        "description": "Timing of full identity checks on inbound trucks at East UK Port (Dover) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkImUK-E",
        "label": "PerPhyChkImUK-E",
        "description": "Percentage of inbound trucks need physical checks (red routed) at East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyCheckTimeImUK-E",
        "label": "PhyCheckTimeImUK-E",
        "description": "Timing of physical checks on inbound trucks at East UK Port (Dover) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkUK-E",
        "label": "PerSecurityChkUK-E",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checksat East UK Port (Dover) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecCheckTimeUK-E",
        "label": "SecCheckTimeUK-E",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at East UK Port (Dover) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "PerGreenTrucksImEU",
        "label": "PerGreenTrucksImEU",
        "description": "Percentage of intbound trucks directed to green route at at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 1.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocCheckTimeImEU",
        "label": "DocCheckTimeImEU",
        "description": "Timing of documentary and sealed identity checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 10.0,
          "scenario_2": 10.0
        }
      },
      {
        "key": "PerFullIdnChkImEU",
        "label": "PerFullIdnChkImEU",
        "description": "Percentage of inbound trucks need full identity checks (orange routed) at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "IdnCheckTimeImEU",
        "label": "IdnCheckTimeImEU",
        "description": "Timing of full identity checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 60.0,
          "scenario_2": 60.0
        }
      },
      {
        "key": "PerPhyChkImEU",
        "label": "PerPhyChkImEU",
        "description": "Percentage of inbound trucks need physical checks (red routed) at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 0.01,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.5,
          "scenario_2": 0.5
        }
      },
      {
        "key": "PhyCheckTimeImEU",
        "label": "PhyCheckTimeImEU",
        "description": "Timing of physical checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 120.0,
          "scenario_2": 120.0
        }
      },
      {
        "key": "PerSecurityChkEU",
        "label": "PerSecurityChkEU",
        "description": "Percentage of inbound trucks for security, license compliance and immegration checksat at West-EU Ports (Calais) (%)",
        "unit": "ratio",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 1.0,
          "scenario_2": 1.0
        }
      },
      {
        "key": "SecCheckTimeEU",
        "label": "SecCheckTimeEU",
        "description": "Timing of the security, license compliance and immegration checks on inbound trucks at West-EU Ports (Calais) (minutes)",
        "unit": "minutes",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "NumCustomOfficerD",
        "label": "NumCustomOfficerD",
        "description": "Number of custom officers at Dublin port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 4.0,
          "scenario_2": 8.0
        }
      },
      {
        "key": "NumSPSUnitOfficerD",
        "label": "NumSPSUnitOfficerD",
        "description": "Number of SPS officer at Dublin port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 4.0,
          "scenario_2": 8.0
        }
      },
      {
        "key": "NumTractorD",
        "label": "NumTractorD",
        "description": "Number of tractor used to twoe an accompanied trucks at Dublin port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 5.0,
          "scenario_2": 5.0
        }
      },
      {
        "key": "NumCustomOfficerR",
        "label": "NumCustomOfficerR",
        "description": "Number of custom officers at Rosslare port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 4.0,
          "scenario_2": 8.0
        }
      },
      {
        "key": "NumSPSUnitOfficerR",
        "label": "NumSPSUnitOfficerR",
        "description": "Number of SPS officer at Rosslare port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 4.0,
          "scenario_2": 8.0
        }
      },
      {
        "key": "NumTractorR",
        "label": "NumTractorR",
        "description": "Number of security and document copmpliance officers at Rosslare port",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      },
      {
        "key": "DocCheckCost",
        "label": "DocCheckCost",
        "description": "Offical documentary check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 50.0,
          "scenario_2": 50.0
        }
      },
      {
        "key": "IdnCheckCost",
        "label": "IdnCheckCost",
        "description": "Offical full identity check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 100.0,
          "scenario_2": 100.0
        }
      },
      {
        "key": "PhyCheckCost",
        "label": "PhyCheckCost",
        "description": "Offical physical check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 500.0,
          "scenario_2": 500.0
        }
      },
      {
        "key": "SecurityCheckCost",
        "label": "SecurityCheckCost",
        "description": "Offical security check cost at Irish ports",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 500.0,
          "scenario_2": 500.0
        }
      },
      {
        "key": "Name",
        "label": "Name",
        "description": "Description",
        "unit": "value",
        "step": 1,
        "values": {
          "as_is": 0.0,
          "scenario_1": 0.0,
          "scenario_2": 0.0
        }
      }
    ]
  }
];
