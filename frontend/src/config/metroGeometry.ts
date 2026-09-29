/**
 * metroGeometry.ts — Hand-curated presentation geometry for Namma Pulse MetroMap.
 * Supports all 5 lines (Purple, Green, Yellow, Pink, Blue) and 7 Interchange Hubs.
 * ViewBox: 0 0 1600 1100
 */

export interface StationGeometry {
  name: string;
  line: "Purple" | "Green" | "Yellow" | "Pink" | "Blue";
  x: number;
  y: number;
  labelX: number;
  labelY: number;
  labelAnchor: "start" | "middle" | "end";
  labelPriority?: "high" | "normal" | "low";
  isInterchange?: boolean;
  isTerminus?: boolean;
  nodeIds: string[];
}

export interface InterchangeCapsule {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rx: number;
  lines: string[];
  nodeIds: string[];
  labelX: number;
  labelY: number;
  labelAnchor: "start" | "middle" | "end";
}

// ---------------------------------------------------------------------------
// 7 Physical Interchange Capsules
// ---------------------------------------------------------------------------

export const INTERCHANGE_CAPSULES: InterchangeCapsule[] = [
  {
    id: "HUB_MAJESTIC",
    name: "Kempegowda Stn., Majestic",
    x: 560, y: 372, width: 40, height: 16, rx: 8,
    lines: ["Purple", "Green"],
    nodeIds: ["PL22", "GL17"],
    labelX: 580, labelY: 406, labelAnchor: "middle",
  },
  {
    id: "HUB_RV_ROAD",
    name: "Rashtreeya Vidyalaya Road",
    x: 560, y: 692, width: 40, height: 16, rx: 8,
    lines: ["Green", "Yellow"],
    nodeIds: ["GL24", "YL01"],
    labelX: 544, labelY: 704, labelAnchor: "end",
  },
  {
    id: "HUB_JAYADEVA",
    name: "Jayadeva Hospital",
    x: 743, y: 692, width: 40, height: 16, rx: 8,
    lines: ["Yellow", "Pink"],
    nodeIds: ["YL03", "PK05"],
    labelX: 763, labelY: 724, labelAnchor: "middle",
  },
  {
    id: "HUB_SILK_BOARD",
    name: "Central Silk Board",
    x: 943, y: 692, width: 40, height: 16, rx: 8,
    lines: ["Yellow", "Blue"],
    nodeIds: ["YL05", "BL23"],
    labelX: 963, labelY: 676, labelAnchor: "middle",
  },
  {
    id: "HUB_MG_ROAD",
    name: "Mahatma Gandhi Road",
    x: 823, y: 372, width: 40, height: 16, rx: 8,
    lines: ["Purple", "Pink"],
    nodeIds: ["PL18", "PK11"],
    labelX: 843, labelY: 358, labelAnchor: "middle",
  },
  {
    id: "HUB_KR_PURA",
    name: "KR Pura",
    x: 1083, y: 232, width: 40, height: 16, rx: 8,
    lines: ["Purple", "Blue"],
    nodeIds: ["PL12", "BL12"],
    labelX: 1103, labelY: 218, labelAnchor: "middle",
  },
  {
    id: "HUB_NAGAWARA",
    name: "Nagawara",
    x: 970, y: 72, width: 40, height: 16, rx: 8,
    lines: ["Pink", "Blue"],
    nodeIds: ["PK18", "BL06"],
    labelX: 990, labelY: 58, labelAnchor: "middle",
  },
];

const NODE_TO_CAPSULE = new Map<string, string>();
INTERCHANGE_CAPSULES.forEach((c) => {
  c.nodeIds.forEach((nid) => NODE_TO_CAPSULE.set(nid, c.id));
});

// ---------------------------------------------------------------------------
// Physical Stations Presentation Coordinates (All 5 Lines)
// ---------------------------------------------------------------------------

export const PHYSICAL_STATIONS: StationGeometry[] = [
  // ── PURPLE LINE ──
  { name: "Challaghatta", line: "Purple", x: 100, y: 860, labelX: 85, labelY: 865, labelAnchor: "end", isTerminus: true, labelPriority: "high", nodeIds: ["PL36"] },
  { name: "Kengeri", line: "Purple", x: 130, y: 830, labelX: 115, labelY: 835, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL35"] },
  { name: "Kengeri Bus Terminal", line: "Purple", x: 160, y: 800, labelX: 145, labelY: 805, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL34"] },
  { name: "Pattanagere", line: "Purple", x: 190, y: 770, labelX: 175, labelY: 775, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL33"] },
  { name: "Rajarajeshwari Nagar", line: "Purple", x: 220, y: 740, labelX: 205, labelY: 745, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL32"] },
  { name: "Jnanabharathi", line: "Purple", x: 250, y: 710, labelX: 235, labelY: 715, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL31"] },
  { name: "Nayandahalli", line: "Purple", x: 280, y: 680, labelX: 265, labelY: 685, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL30"] },
  { name: "Mysuru Road", line: "Purple", x: 310, y: 650, labelX: 295, labelY: 655, labelAnchor: "end", labelPriority: "high", nodeIds: ["PL29"] },
  { name: "Deepanjali Nagar", line: "Purple", x: 340, y: 620, labelX: 325, labelY: 625, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL28"] },
  { name: "Attiguppe", line: "Purple", x: 370, y: 590, labelX: 355, labelY: 595, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL27"] },
  { name: "Vijayanagar", line: "Purple", x: 370, y: 530, labelX: 355, labelY: 535, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL26"] },
  { name: "Hosahalli", line: "Purple", x: 370, y: 480, labelX: 355, labelY: 485, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL25"] },
  { name: "Magadi Road", line: "Purple", x: 370, y: 430, labelX: 355, labelY: 435, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL24"] },
  { name: "KSR City Railway Station", line: "Purple", x: 450, y: 380, labelX: 450, labelY: 360, labelAnchor: "middle", labelPriority: "high", nodeIds: ["PL23"] },
  { name: "Kempegowda Stn., Majestic", line: "Purple", x: 580, y: 380, labelX: 580, labelY: 406, labelAnchor: "middle", isInterchange: true, labelPriority: "high", nodeIds: ["PL22", "GL17"] },
  { name: "Sir M. Visvesvaraya Station (Central College)", line: "Purple", x: 650, y: 380, labelX: 650, labelY: 360, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL21"] },
  { name: "Dr. B.R. Ambedkar Station (Vidhana Soudha)", line: "Purple", x: 710, y: 380, labelX: 710, labelY: 405, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL20"] },
  { name: "Cubbon Park", line: "Purple", x: 770, y: 380, labelX: 770, labelY: 360, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL19"] },
  { name: "Mahatma Gandhi Road (MG Road)", line: "Purple", x: 843, y: 380, labelX: 843, labelY: 358, labelAnchor: "middle", isInterchange: true, labelPriority: "high", nodeIds: ["PL18", "PK11"] },
  { name: "Trinity", line: "Purple", x: 900, y: 380, labelX: 900, labelY: 405, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL17"] },
  { name: "Halasuru", line: "Purple", x: 950, y: 380, labelX: 950, labelY: 360, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL16"] },
  { name: "Indiranagar", line: "Purple", x: 1000, y: 380, labelX: 1000, labelY: 405, labelAnchor: "middle", labelPriority: "high", nodeIds: ["PL16"] },
  { name: "Swami Vivekananda Road", line: "Purple", x: 1000, y: 310, labelX: 985, labelY: 314, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PL15"] },
  { name: "Baiyappanahalli", line: "Purple", x: 1000, y: 260, labelX: 985, labelY: 264, labelAnchor: "end", labelPriority: "high", nodeIds: ["PL14"] },
  { name: "Benniganahalli", line: "Purple", x: 1030, y: 240, labelX: 1030, labelY: 222, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL13"] },
  { name: "Krishnarajapura (KR Pura)", line: "Purple", x: 1103, y: 240, labelX: 1103, labelY: 218, labelAnchor: "middle", isInterchange: true, labelPriority: "high", nodeIds: ["PL12", "BL12"] },
  { name: "Singayyanapalya", line: "Purple", x: 1170, y: 240, labelX: 1170, labelY: 222, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL11"] },
  { name: "Garudacharapalya", line: "Purple", x: 1230, y: 240, labelX: 1230, labelY: 222, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL10"] },
  { name: "Hoodi", line: "Purple", x: 1280, y: 270, labelX: 1295, labelY: 265, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PL09"] },
  { name: "Seetharam Palya", line: "Purple", x: 1320, y: 310, labelX: 1335, labelY: 315, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PL08"] },
  { name: "Kundalahalli", line: "Purple", x: 1360, y: 340, labelX: 1375, labelY: 345, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PL07"] },
  { name: "Nallurhalli", line: "Purple", x: 1410, y: 320, labelX: 1425, labelY: 325, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PL06"] },
  { name: "Sri Sathya Sai Hospital", line: "Purple", x: 1440, y: 280, labelX: 1455, labelY: 285, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PL05"] },
  { name: "Pattandur Agrahara", line: "Purple", x: 1470, y: 240, labelX: 1470, labelY: 222, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL04"] },
  { name: "Kadugodi Tree Park", line: "Purple", x: 1500, y: 240, labelX: 1500, labelY: 222, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["PL03"] },
  { name: "Channasandra", line: "Purple", x: 1530, y: 240, labelX: 1545, labelY: 245, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PL02"] },
  { name: "Whitefield (Kadugodi)", line: "Purple", x: 1530, y: 180, labelX: 1515, labelY: 185, labelAnchor: "end", isTerminus: true, labelPriority: "high", nodeIds: ["PL01"] },

  // ── GREEN LINE ──
  { name: "Madavara", line: "Green", x: 160, y: 40, labelX: 145, labelY: 45, labelAnchor: "end", isTerminus: true, labelPriority: "high", nodeIds: ["GL01"] },
  { name: "Chikkabidarakallu", line: "Green", x: 190, y: 70, labelX: 175, labelY: 75, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL02"] },
  { name: "Manjunathanagar", line: "Green", x: 220, y: 100, labelX: 205, labelY: 105, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL03"] },
  { name: "Nagasandra", line: "Green", x: 250, y: 130, labelX: 235, labelY: 135, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL04"] },
  { name: "Dasarahalli", line: "Green", x: 280, y: 160, labelX: 265, labelY: 165, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL05"] },
  { name: "Jalahalli", line: "Green", x: 310, y: 190, labelX: 295, labelY: 195, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL06"] },
  { name: "Peenya Industry", line: "Green", x: 340, y: 220, labelX: 325, labelY: 225, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL07"] },
  { name: "Peenya", line: "Green", x: 370, y: 250, labelX: 355, labelY: 255, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL08"] },
  { name: "Goraguntepalya", line: "Green", x: 400, y: 280, labelX: 385, labelY: 285, labelAnchor: "end", labelPriority: "normal", nodeIds: ["GL09"] },
  { name: "Yeshwanthpur", line: "Green", x: 430, y: 310, labelX: 430, labelY: 292, labelAnchor: "middle", labelPriority: "high", nodeIds: ["GL10"] },
  { name: "Sandal Soap Factory", line: "Green", x: 470, y: 310, labelX: 470, labelY: 330, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["GL11"] },
  { name: "Mahalakshmi", line: "Green", x: 500, y: 310, labelX: 500, labelY: 292, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["GL12"] },
  { name: "Rajajinagar", line: "Green", x: 520, y: 310, labelX: 520, labelY: 330, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["GL13"] },
  { name: "Mahakavi Kuvempu Road", line: "Green", x: 540, y: 310, labelX: 540, labelY: 292, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["GL14"] },
  { name: "Srirampura", line: "Green", x: 580, y: 270, labelX: 595, labelY: 274, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL15"] },
  { name: "Sampige Road (Mantri Square)", line: "Green", x: 580, y: 325, labelX: 595, labelY: 329, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL16"] },
  { name: "Chickpete", line: "Green", x: 580, y: 430, labelX: 595, labelY: 434, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL18"] },
  { name: "Krishna Rajendra Market (KR Market)", line: "Green", x: 580, y: 480, labelX: 595, labelY: 484, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL19"] },
  { name: "National College", line: "Green", x: 580, y: 530, labelX: 595, labelY: 534, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL20"] },
  { name: "Lalbagh", line: "Green", x: 580, y: 570, labelX: 595, labelY: 574, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL21"] },
  { name: "South End Circle", line: "Green", x: 580, y: 610, labelX: 595, labelY: 614, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL22"] },
  { name: "Jayanagar", line: "Green", x: 580, y: 650, labelX: 595, labelY: 654, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL23"] },
  { name: "Rashtreeya Vidyalaya Road (RV Road)", line: "Green", x: 580, y: 700, labelX: 544, labelY: 704, labelAnchor: "end", isInterchange: true, labelPriority: "high", nodeIds: ["GL24", "YL01"] },
  { name: "Banashankari", line: "Green", x: 580, y: 750, labelX: 595, labelY: 754, labelAnchor: "start", labelPriority: "high", nodeIds: ["GL25"] },
  { name: "Jaya Prakash Nagar", line: "Green", x: 580, y: 790, labelX: 595, labelY: 794, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL26"] },
  { name: "Yelachenahalli", line: "Green", x: 560, y: 820, labelX: 575, labelY: 824, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL27"] },
  { name: "Konanakunte Cross", line: "Green", x: 520, y: 860, labelX: 535, labelY: 865, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL28"] },
  { name: "Doddakallasandra", line: "Green", x: 480, y: 900, labelX: 495, labelY: 905, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL29"] },
  { name: "Vajrahalli", line: "Green", x: 440, y: 940, labelX: 455, labelY: 945, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL30"] },
  { name: "Thalaghattapura", line: "Green", x: 400, y: 980, labelX: 415, labelY: 985, labelAnchor: "start", labelPriority: "normal", nodeIds: ["GL31"] },
  { name: "Silk Institute", line: "Green", x: 360, y: 1020, labelX: 345, labelY: 1025, labelAnchor: "end", isTerminus: true, labelPriority: "high", nodeIds: ["GL32"] },

  // ── YELLOW LINE ──
  { name: "Ragigudda", line: "Yellow", x: 660, y: 700, labelX: 660, labelY: 724, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["YL02"] },
  { name: "Jayadeva Hospital", line: "Yellow", x: 763, y: 700, labelX: 763, labelY: 724, labelAnchor: "middle", isInterchange: true, labelPriority: "high", nodeIds: ["YL03", "PK05"] },
  { name: "BTM Layout", line: "Yellow", x: 860, y: 700, labelX: 860, labelY: 724, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["YL04"] },
  { name: "Central Silk Board", line: "Yellow", x: 963, y: 700, labelX: 963, labelY: 676, labelAnchor: "middle", isInterchange: true, labelPriority: "high", nodeIds: ["YL05", "BL23"] },
  { name: "Bommanahalli", line: "Yellow", x: 1010, y: 750, labelX: 1025, labelY: 755, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL06"] },
  { name: "Hongasandra", line: "Yellow", x: 1050, y: 790, labelX: 1065, labelY: 795, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL07"] },
  { name: "Kudlu Gate", line: "Yellow", x: 1090, y: 830, labelX: 1105, labelY: 835, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL08"] },
  { name: "Singasandra", line: "Yellow", x: 1130, y: 870, labelX: 1145, labelY: 875, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL09"] },
  { name: "Hosa Road", line: "Yellow", x: 1170, y: 910, labelX: 1185, labelY: 915, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL10"] },
  { name: "Beratena Agrahara", line: "Yellow", x: 1210, y: 950, labelX: 1225, labelY: 955, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL11"] },
  { name: "Electronic City", line: "Yellow", x: 1250, y: 990, labelX: 1265, labelY: 995, labelAnchor: "start", labelPriority: "high", nodeIds: ["YL12"] },
  { name: "Infosys Foundation Konappana Agrahara", line: "Yellow", x: 1290, y: 1020, labelX: 1305, labelY: 1025, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL13"] },
  { name: "Huskur Road", line: "Yellow", x: 1330, y: 1040, labelX: 1345, labelY: 1045, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL14"] },
  { name: "Hebbagodi", line: "Yellow", x: 1370, y: 1055, labelX: 1385, labelY: 1060, labelAnchor: "start", labelPriority: "normal", nodeIds: ["YL15"] },
  { name: "Bommasandra", line: "Yellow", x: 1410, y: 1070, labelX: 1425, labelY: 1075, labelAnchor: "start", isInterchange: false, isTerminus: true, labelPriority: "high", nodeIds: ["YL16"] },

  // ── PINK LINE (2025 Reference) ──
  { name: "Kalena Agrahara", line: "Pink", x: 763, y: 1040, labelX: 748, labelY: 1045, labelAnchor: "end", isTerminus: true, labelPriority: "high", nodeIds: ["PK01"] },
  { name: "Hulimavu", line: "Pink", x: 763, y: 980, labelX: 748, labelY: 985, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK02"] },
  { name: "IIM Bangalore", line: "Pink", x: 763, y: 920, labelX: 748, labelY: 925, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK03"] },
  { name: "JP Nagar 4th Phase", line: "Pink", x: 763, y: 860, labelX: 748, labelY: 865, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK04"] },
  { name: "Tavarekere", line: "Pink", x: 763, y: 620, labelX: 748, labelY: 625, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK06"] },
  { name: "Dairy Circle", line: "Pink", x: 763, y: 560, labelX: 748, labelY: 565, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK07"] },
  { name: "Lakkasandra", line: "Pink", x: 763, y: 500, labelX: 748, labelY: 505, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK08"] },
  { name: "Langford Town", line: "Pink", x: 763, y: 440, labelX: 748, labelY: 445, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK09"] },
  { name: "Rashtriya Military School", line: "Pink", x: 763, y: 410, labelX: 748, labelY: 415, labelAnchor: "end", labelPriority: "normal", nodeIds: ["PK10"] },
  { name: "Shivajinagar", line: "Pink", x: 843, y: 310, labelX: 858, labelY: 315, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PK12"] },
  { name: "Cantonment", line: "Pink", x: 843, y: 250, labelX: 858, labelY: 255, labelAnchor: "start", labelPriority: "high", nodeIds: ["PK13"] },
  { name: "Pottery Town", line: "Pink", x: 860, y: 200, labelX: 875, labelY: 205, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PK14"] },
  { name: "Tannery Road", line: "Pink", x: 890, y: 160, labelX: 905, labelY: 165, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PK15"] },
  { name: "Venkateshpura", line: "Pink", x: 920, y: 130, labelX: 935, labelY: 135, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PK16"] },
  { name: "Kadugundanahalli", line: "Pink", x: 950, y: 100, labelX: 965, labelY: 105, labelAnchor: "start", labelPriority: "normal", nodeIds: ["PK17"] },

  // ── BLUE LINE (2025 Reference) ──
  { name: "KIA Airport", line: "Blue", x: 720, y: 30, labelX: 705, labelY: 35, labelAnchor: "end", isTerminus: true, labelPriority: "high", nodeIds: ["BL01"] },
  { name: "Kodigehalli", line: "Blue", x: 770, y: 30, labelX: 770, labelY: 15, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["BL02"] },
  { name: "Hebbal", line: "Blue", x: 830, y: 30, labelX: 830, labelY: 15, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["BL03"] },
  { name: "Kempapura", line: "Blue", x: 890, y: 30, labelX: 890, labelY: 15, labelAnchor: "middle", labelPriority: "normal", nodeIds: ["BL04"] },
  { name: "Veersannapalya", line: "Blue", x: 940, y: 50, labelX: 955, labelY: 50, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL05"] },
  { name: "HBR Layout", line: "Blue", x: 1050, y: 110, labelX: 1065, labelY: 115, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL07"] },
  { name: "Kalyan Nagar", line: "Blue", x: 1090, y: 140, labelX: 1105, labelY: 145, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL08"] },
  { name: "HRBR Layout", line: "Blue", x: 1120, y: 170, labelX: 1135, labelY: 175, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL09"] },
  { name: "Horamavu", line: "Blue", x: 1140, y: 190, labelX: 1155, labelY: 195, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL10"] },
  { name: "Kasturinagar", line: "Blue", x: 1150, y: 210, labelX: 1165, labelY: 215, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL11"] },
  { name: "Mahadevapura", line: "Blue", x: 1103, y: 310, labelX: 1118, labelY: 315, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL13"] },
  { name: "DRDO Sports Complex", line: "Blue", x: 1103, y: 370, labelX: 1118, labelY: 375, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL14"] },
  { name: "Doddanekundi", line: "Blue", x: 1103, y: 430, labelX: 1118, labelY: 435, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL15"] },
  { name: "ISRO (Karthik Nagar)", line: "Blue", x: 1103, y: 490, labelX: 1118, labelY: 495, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL16"] },
  { name: "Marathahalli", line: "Blue", x: 1070, y: 550, labelX: 1085, labelY: 555, labelAnchor: "start", labelPriority: "high", nodeIds: ["BL17"] },
  { name: "Kadubeesanahalli", line: "Blue", x: 1040, y: 590, labelX: 1055, labelY: 595, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL18"] },
  { name: "Devarabeesanahalli", line: "Blue", x: 1010, y: 620, labelX: 1025, labelY: 625, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL19"] },
  { name: "Bellandur", line: "Blue", x: 990, y: 640, labelX: 1005, labelY: 645, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL20"] },
  { name: "Iblur", line: "Blue", x: 980, y: 660, labelX: 995, labelY: 665, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL21"] },
  { name: "Agara Lake", line: "Blue", x: 970, y: 675, labelX: 985, labelY: 680, labelAnchor: "start", labelPriority: "normal", nodeIds: ["BL22"] },
];

// ---------------------------------------------------------------------------
// SVG Line Paths for all 5 lines
// ---------------------------------------------------------------------------

export const METRO_LINE_PATHS: Record<string, string> = {
  Purple: [
    "M 100 860 L 370 590 L 370 430 Q 370 380 450 380 L 1000 380 L 1000 260 Q 1000 240 1030 240 L 1230 240 L 1280 270 L 1360 340 L 1410 320 L 1440 280 L 1470 240 L 1530 240 L 1530 180"
  ].join(" "),

  Green: [
    "M 160 40 L 430 310 L 520 310 Q 580 310 580 270 L 580 790 L 560 820 L 360 1020"
  ].join(" "),

  Yellow: [
    "M 580 700 L 963 700 L 1410 1070"
  ].join(" "),

  Pink: [
    "M 763 1040 L 763 410 L 843 380 L 843 250 L 990 80"
  ].join(" "),

  Blue: [
    "M 720 30 L 890 30 L 990 80 L 1150 210 L 1103 240 L 1103 490 L 963 700"
  ].join(" "),
};

// ---------------------------------------------------------------------------
// Lookup Utilities
// ---------------------------------------------------------------------------

const GEOMETRY_BY_NODE = new Map<string, StationGeometry>();
const GEOMETRY_BY_NAME = new Map<string, StationGeometry>();

PHYSICAL_STATIONS.forEach((st) => {
  GEOMETRY_BY_NAME.set(st.name.toLowerCase(), st);
  st.nodeIds.forEach((nid) => GEOMETRY_BY_NODE.set(nid, st));
});

export function getStationGeometry(idOrName: string): StationGeometry | undefined {
  if (!idOrName) return undefined;
  return GEOMETRY_BY_NODE.get(idOrName) || GEOMETRY_BY_NAME.get(idOrName.toLowerCase());
}
