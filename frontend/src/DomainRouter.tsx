import { Routes, Route } from "react-router-dom";
import { useMemo } from "react";
import DomainLayout, { type NavItem } from "./layouts/DomainLayout";

// Pool (existing) pages
import BlockList from "./pages/BlockList";
import BlockDetail from "./pages/BlockDetail";
import NodeList from "./pages/NodeList";
import NodeDetail from "./pages/NodeDetail";

// Epoch pages
import EpochBrowser from "./pages/epoch/EpochBrowser";
import EpochDetail from "./pages/epoch/EpochDetail";
import YieldBreakdown from "./pages/epoch/YieldBreakdown";
import SiliconLadder from "./pages/epoch/SiliconLadder";

// Ledger pages
import LedgerTimeline from "./pages/ledger/LedgerTimeline";
import AnchorDetail from "./pages/ledger/AnchorDetail";

// Energy pages
import EnergyDashboard from "./pages/energy/EnergyDashboard";
import CostFrontier from "./pages/energy/CostFrontier";
import TransformEconomics from "./pages/energy/TransformEconomics";

// Protocol pages
import ProtocolHome from "./pages/protocol/ProtocolHome";
import WhitepaperViewer from "./pages/protocol/WhitepaperViewer";

const DOMAIN_MAP: Record<string, string> = {
  "swarmchain.eth.limo": "pool",
  "swarmepoch.eth.limo": "epoch",
  "swarmledger.eth.limo": "ledger",
  "swarmenergy.eth.limo": "energy",
  "swarmprotocol.eth.limo": "protocol",
};

function detectDomain(): string {
  // Support ?domain= query param for dev testing
  const params = new URLSearchParams(window.location.search);
  const domainParam = params.get("domain");
  if (domainParam && ["pool", "epoch", "ledger", "energy", "protocol"].includes(domainParam)) {
    return domainParam;
  }

  const hostname = window.location.hostname;
  return DOMAIN_MAP[hostname] ?? "pool";
}

interface DomainConfig {
  name: string;
  subtitle: string;
  accent: string;
  navSection: string;
  navItems: NavItem[];
  showSystemStatus: boolean;
  pollingInterval: number;
}

const DOMAIN_CONFIGS: Record<string, DomainConfig> = {
  pool: {
    name: "SwarmChain",
    subtitle: "Block Explorer",
    accent: "blue",
    navSection: "Explorer",
    navItems: [
      { to: "/", label: "Blocks", icon: "\u26D3" },
      { to: "/nodes", label: "Nodes", icon: "\u2699" },
    ],
    showSystemStatus: true,
    pollingInterval: 5000,
  },
  epoch: {
    name: "SwarmEpoch",
    subtitle: "Epoch Intelligence",
    accent: "purple",
    navSection: "Epochs",
    navItems: [
      { to: "/", label: "Epochs", icon: "\uD83D\uDCC8" },
    ],
    showSystemStatus: false,
    pollingInterval: 10000,
  },
  ledger: {
    name: "SwarmLedger",
    subtitle: "Provenance Chain",
    accent: "amber",
    navSection: "Ledger",
    navItems: [
      { to: "/", label: "Timeline", icon: "\uD83D\uDD17" },
    ],
    showSystemStatus: false,
    pollingInterval: 10000,
  },
  energy: {
    name: "SwarmEnergy",
    subtitle: "Compute Economics",
    accent: "emerald",
    navSection: "Energy",
    navItems: [
      { to: "/", label: "Dashboard", icon: "\u26A1" },
      { to: "/cost-frontier", label: "Cost Frontier", icon: "\uD83C\uDFAF" },
      { to: "/transforms", label: "Transforms", icon: "\uD83D\uDD27" },
    ],
    showSystemStatus: false,
    pollingInterval: 10000,
  },
  protocol: {
    name: "SwarmProtocol",
    subtitle: "Protocol Specification",
    accent: "cyan",
    navSection: "Protocol",
    navItems: [
      { to: "/", label: "Home", icon: "\uD83C\uDFE0" },
      { to: "/whitepaper", label: "Whitepaper", icon: "\uD83D\uDCC4" },
    ],
    showSystemStatus: false,
    pollingInterval: 30000,
  },
};

function PoolApp() {
  return (
    <Routes>
      <Route path="/" element={<BlockList />} />
      <Route path="/blocks/:blockId" element={<BlockDetail />} />
      <Route path="/nodes" element={<NodeList />} />
      <Route path="/nodes/:nodeId" element={<NodeDetail />} />
    </Routes>
  );
}

function EpochApp() {
  return (
    <Routes>
      <Route path="/" element={<EpochBrowser />} />
      <Route path="/epoch/:epochId" element={<EpochDetail />} />
      <Route path="/epoch/:epochId/yield" element={<YieldBreakdown />} />
      <Route path="/epoch/:epochId/ladder" element={<SiliconLadder />} />
    </Routes>
  );
}

function LedgerApp() {
  return (
    <Routes>
      <Route path="/" element={<LedgerTimeline />} />
      <Route path="/anchor/:window" element={<AnchorDetail />} />
    </Routes>
  );
}

function EnergyApp() {
  return (
    <Routes>
      <Route path="/" element={<EnergyDashboard />} />
      <Route path="/cost-frontier" element={<CostFrontier />} />
      <Route path="/transforms" element={<TransformEconomics />} />
    </Routes>
  );
}

function ProtocolApp() {
  return (
    <Routes>
      <Route path="/" element={<ProtocolHome />} />
      <Route path="/whitepaper" element={<WhitepaperViewer />} />
    </Routes>
  );
}

const DOMAIN_APPS: Record<string, () => JSX.Element> = {
  pool: PoolApp,
  epoch: EpochApp,
  ledger: LedgerApp,
  energy: EnergyApp,
  protocol: ProtocolApp,
};

export default function DomainRouter() {
  const domain = useMemo(() => detectDomain(), []);
  const config = DOMAIN_CONFIGS[domain] ?? DOMAIN_CONFIGS.pool;
  const AppComponent = DOMAIN_APPS[domain] ?? PoolApp;

  return (
    <DomainLayout
      domainName={config.name}
      subtitle={config.subtitle}
      accentColor={config.accent}
      navSection={config.navSection}
      navItems={config.navItems}
      showSystemStatus={config.showSystemStatus}
      pollingInterval={config.pollingInterval}
    >
      <AppComponent />
    </DomainLayout>
  );
}
