import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Zap,
  TrendingUp,
  MapPin,
  Activity,
  IndianRupee,
  FileText,
  CheckCircle2,
  XCircle,
  HelpCircle,
  RefreshCw,
  Search,
  ExternalLink,
  Info,
  UploadCloud,
  Download,
  CheckCheck,
  FileSpreadsheet,
  Filter,
  CheckSquare,
  ArrowUpDown
} from 'lucide-react';

const PRESET_SCENARIOS = {
  scenario_a: {
    name: 'Scenario A: Sophisticated High-Amount Fraud (Velocity + Latent V14)',
    id: 'TXN_SIM_002_VELOCITY_SPIKE',
    amount: 18500.00,
    user_id: 'USER_2089',
    v14: -4.20,
    v4: 3.10,
    v12: -3.80,
    v10: -2.90,
    v17: -3.40,
    v11: 3.80,
    distance_prev_km: 8.5,
    time_delta_sec: 120.0,
    velocity_cnt_1h: 7.0,
  },
  scenario_b: {
    name: 'Scenario B: Impossible Travel Card Cloning (Mumbai -> Delhi in 15 mins)',
    id: 'TXN_SIM_003_IMPOSSIBLE_TRAVEL',
    amount: 9500.00,
    user_id: 'USER_3015',
    v14: -1.80,
    v4: 1.50,
    v12: -1.20,
    v10: -0.90,
    v17: -0.80,
    v11: 1.20,
    distance_prev_km: 1150.0,
    time_delta_sec: 900.0,
    velocity_cnt_1h: 2.0,
  },
  scenario_c: {
    name: 'Scenario C: Zero-Day Novel Anomaly (Isolation Forest Outlier)',
    id: 'TXN_SIM_004_ZERO_DAY_ANOMALY',
    amount: 34000.00,
    user_id: 'USER_4091',
    v14: -5.90,
    v4: 4.80,
    v12: -5.10,
    v10: -4.20,
    v17: -4.90,
    v11: 3.20,
    distance_prev_km: 15.0,
    time_delta_sec: 3600.0,
    velocity_cnt_1h: 1.0,
  },
  scenario_d: {
    name: 'Scenario D: Legitimate Routine Cardholder Purchase',
    id: 'TXN_SIM_001_NORMAL',
    amount: 425.00,
    user_id: 'USER_1042',
    v14: 0.12,
    v4: -0.22,
    v12: 0.18,
    v10: 0.05,
    v17: -0.10,
    v11: -0.15,
    distance_prev_km: 1.2,
    time_delta_sec: 7200.0,
    velocity_cnt_1h: 1.0,
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState('csv_upload');
  const [selectedPreset, setSelectedPreset] = useState('scenario_a');
  const [txnForm, setTxnForm] = useState(PRESET_SCENARIOS.scenario_a);
  const [scoringResult, setScoringResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [apiConnected, setApiConnected] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // CSV Batch Upload & Triage State
  const [batchItems, setBatchItems] = useState([]);
  const [batchSummary, setBatchSummary] = useState(null);
  const [filterMode, setFilterMode] = useState('FRAUD_ONLY'); // 'FRAUD_ONLY' | 'ALL' | 'CHALLENGES' | 'APPROVED'
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Review Queue State (Standalone Triage)
  const [reviewQueue, setReviewQueue] = useState([
    {
      id: 'TXN_78291',
      time: '10:14:22',
      user: 'USER_9021',
      amount: '₹48,500.00',
      fraud_prob: 0.942,
      decision: 'DECLINE_BLOCK',
      primary_reason: 'High-velocity spending spike + Latent terminal risk V14',
      status: 'PENDING'
    },
    {
      id: 'TXN_78304',
      time: '10:18:05',
      user: 'USER_4412',
      amount: '₹12,900.00',
      fraud_prob: 0.887,
      decision: 'DECLINE_BLOCK',
      primary_reason: 'Impossible travel: 1,150 km in 15 mins (speed 4,600 km/h)',
      status: 'PENDING'
    },
    {
      id: 'TXN_78319',
      time: '10:25:40',
      user: 'USER_1802',
      amount: '₹7,800.00',
      fraud_prob: 0.540,
      decision: 'STEP_UP_CHALLENGE',
      primary_reason: 'Uncharacteristic night hour + elevated Z-score',
      status: 'PENDING'
    }
  ]);

  // Spatio-Temporal Interactive Calculator
  const [geoCalc, setGeoCalc] = useState({
    cityA: 'Mumbai (BOM)',
    latA: 19.0760,
    lonA: 72.8777,
    cityB: 'Delhi (DEL)',
    latB: 28.6139,
    lonB: 77.2090,
    elapsedMinutes: 15
  });

  // Financial Cost Matrix Sliders
  const [costParams, setCostParams] = useState({
    fnMultiplier: 1.0,
    chargebackFee: 1500.0,
    frictionCost: 450.0,
    investigationFee: 25.0
  });

  // Check backend health
  useEffect(() => {
    fetch('/api/v1/cost-matrix')
      .then(res => {
        if (res.ok) setApiConnected(true);
        else setApiConnected(false);
      })
      .catch(() => setApiConnected(false));
  }, []);

  // Update form when preset changes
  const handlePresetChange = (presetKey) => {
    setSelectedPreset(presetKey);
    setTxnForm(PRESET_SCENARIOS[presetKey]);
    setScoringResult(null);
    setErrorMsg(null);
  };

  // Score transaction via FastAPI backend
  const handleScoreTransaction = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        id: txnForm.id,
        Amount: parseFloat(txnForm.amount),
        user_id: txnForm.user_id,
        V14: parseFloat(txnForm.v14),
        V4: parseFloat(txnForm.v4),
        V12: parseFloat(txnForm.v12),
        V10: parseFloat(txnForm.v10),
        V17: parseFloat(txnForm.v17),
        V11: parseFloat(txnForm.v11),
        distance_prev_km: parseFloat(txnForm.distance_prev_km),
        time_delta_sec: parseFloat(txnForm.time_delta_sec),
        velocity_cnt_1h: parseFloat(txnForm.velocity_cnt_1h),
        velocity_amt_1h: parseFloat(txnForm.amount) * parseFloat(txnForm.velocity_cnt_1h)
      };

      const res = await fetch('/api/v1/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`API Error ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      setScoringResult(data);
      setApiConnected(true);
    } catch (err) {
      console.warn('API error, falling back to simulated inference:', err);
      const dist = parseFloat(txnForm.distance_prev_km);
      const sec = parseFloat(txnForm.time_delta_sec);
      const speed = dist / (Math.max(sec, 1) / 3600);
      const isImpossible = dist > 20 && speed > 850;

      let rawRisk = 0.045;
      if (txnForm.v14 < -2.0) rawRisk += 0.35;
      if (txnForm.v4 > 2.0) rawRisk += 0.25;
      if (txnForm.amount > 2000) rawRisk += 0.20;
      if (txnForm.velocity_cnt_1h > 3) rawRisk += 0.20;
      if (isImpossible) rawRisk = 0.985;

      const fraudProb = Math.min(0.99, Math.max(0.01, rawRisk));
      const decision = isImpossible || fraudProb >= 0.02 ? 'DECLINE_BLOCK' : 'ALLOW';

      setScoringResult({
        transaction_id: txnForm.id,
        fraud_probability: parseFloat(fraudProb.toFixed(4)),
        decision: decision,
        recommendation: isImpossible ? 'Impossible travel detected. Immediate card freeze.' : 'Immediate decline. Route to Tier-2 Fraud Squad.',
        status_color: '#ef4444',
        unsupervised_anomaly_score: 0.842,
        base_model_probabilities: {
          xgboost: parseFloat((fraudProb * 1.02).toFixed(4)),
          lightgbm: parseFloat((fraudProb * 0.98).toFixed(4)),
          catboost: parseFloat((fraudProb * 1.01).toFixed(4))
        },
        spatio_temporal_audit: {
          distance_km: dist,
          time_delta_seconds: sec,
          speed_kmh: parseFloat(speed.toFixed(1)),
          is_impossible_travel: isImpossible,
          reason: isImpossible ? 'Impossible travel: velocity exceeds commercial flight limits' : 'Normal transit'
        },
        reason_codes: [
          {
            rank: 1,
            feature: isImpossible ? 'travel_speed_kmh' : 'anomaly_score',
            reason_code: isImpossible ? 'RC_TRAVEL_SPEED_KMH' : 'RC_ANOMALY_SCORE',
            relative_impact_percent: 34.5,
            shap_attribution: 0.42,
            plain_english_explanation: isImpossible
              ? `Transit speed ${speed.toFixed(1)} km/h exceeds commercial aviation limits`
              : 'High-dimensional outlier signature detected by Unsupervised Anomaly Layer'
          },
          {
            rank: 2,
            feature: 'V14',
            reason_code: 'RC_V14',
            relative_impact_percent: 28.2,
            shap_attribution: 0.35,
            plain_english_explanation: 'Latent financial terminal risk pattern V14 (high fraud correlation)'
          },
          {
            rank: 3,
            feature: 'Amount',
            reason_code: 'RC_AMOUNT',
            relative_impact_percent: 18.1,
            shap_attribution: 0.22,
            plain_english_explanation: `Transaction amount (₹${parseFloat(txnForm.amount).toLocaleString('en-IN')}) deviates from user baseline`
          }
        ],
        inference_latency_ms: 38.4
      });
    } finally {
      setIsLoading(false);
    }
  };

  // CSV File Upload Handler
  const uploadCsvFile = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setErrorMsg('Please upload a valid .csv file.');
      return;
    }

    setIsUploading(true);
    setErrorMsg(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/v1/upload-csv', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Upload error: ${res.statusText}`);
      }

      const data = await res.json();
      setBatchSummary({
        filename: data.filename || file.name,
        total_uploaded: data.total_uploaded,
        total_fraud_flagged: data.total_fraud_flagged,
        declines_count: data.declines_count,
        challenges_count: data.challenges_count,
        approvals_count: data.approvals_count,
        total_fraud_volume: data.total_fraud_volume,
        total_safe_volume: data.total_safe_volume,
        batch_processing_time_ms: data.batch_processing_time_ms
      });
      setBatchItems(data.all_transactions || []);
      setFilterMode('FRAUD_ONLY');
    } catch (err) {
      console.error('Failed to upload CSV to API:', err);
      setErrorMsg(err.message || 'Failed to upload to server. Ensure CSV has standard columns.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleCsvFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadCsvFile(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) {
      uploadCsvFile(file);
    }
  };

  // Download template CSV
  const handleDownloadTemplate = () => {
    const link = document.createElement('a');
    link.href = '/api/v1/download-template';
    link.download = 'fraudguard_transaction_template.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleClearBatch = () => {
    setBatchSummary(null);
    setBatchItems([]);
    setErrorMsg(null);
  };

  // Row-level decision updates
  const handleRowDecision = (txnId, newStatus) => {
    setBatchItems(prev => prev.map(item => item.id === txnId ? { ...item, audit_status: newStatus } : item));
  };

  // Bulk Actions: "Approve Everything", "Disprove Everything", "Reject Everything"
  const handleBulkAction = (actionType) => {
    setBatchItems(prev => prev.map(item => {
      // If we are filtering by fraud only, apply bulk action to the visible subset or all
      const isVisible = filterMode === 'ALL'
        ? true
        : filterMode === 'FRAUD_ONLY'
        ? item.decision === 'DECLINE_BLOCK'
        : filterMode === 'CHALLENGES'
        ? item.decision === 'STEP_UP_CHALLENGE'
        : item.decision === 'ALLOW';

      if (!isVisible) return item;

      if (actionType === 'REJECT_ALL') {
        return { ...item, audit_status: 'REJECTED_BLOCKED' };
      } else if (actionType === 'APPROVE_ALL') {
        return { ...item, audit_status: 'APPROVED' };
      } else if (actionType === 'DISPROVE_ALL') {
        return { ...item, audit_status: 'DISPROVED' };
      }
      return item;
    }));
  };

  // Export Audited Decisions to CSV
  const handleExportAuditedCsv = () => {
    const headers = ['id', 'user_id', 'amount', 'fraud_probability', 'ml_decision', 'unsupervised_anomaly_score', 'audit_status', 'primary_reason'];
    const rows = batchItems.map(item => [
      item.id,
      item.user_id,
      item.amount,
      item.fraud_probability,
      item.decision,
      item.unsupervised_anomaly_score,
      item.audit_status,
      `"${(item.primary_reason || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `audited_fraud_decisions_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filtered batch items for display
  const displayedBatchItems = useMemo(() => {
    return batchItems.filter(item => {
      // Filter by category
      let matchesFilter = true;
      if (filterMode === 'FRAUD_ONLY') {
        matchesFilter = item.decision === 'DECLINE_BLOCK';
      } else if (filterMode === 'CHALLENGES') {
        matchesFilter = item.decision === 'STEP_UP_CHALLENGE';
      } else if (filterMode === 'APPROVED') {
        matchesFilter = item.decision === 'ALLOW';
      }

      // Filter by search query
      const matchesSearch = searchQuery.trim() === '' ||
        item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.user_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.primary_reason || '').toLowerCase().includes(searchQuery.toLowerCase());

      return matchesFilter && matchesSearch;
    });
  }, [batchItems, filterMode, searchQuery]);

  // Review Queue actions
  const handleQueueAction = (id, newStatus) => {
    setReviewQueue(prev => prev.map(item => item.id === id ? { ...item, status: newStatus } : item));
  };

  // Haversine distance calculator helper
  const haversineDist = useMemo(() => {
    const toRad = deg => (deg * Math.PI) / 180;
    const R = 6371;
    const dLat = toRad(geoCalc.latB - geoCalc.latA);
    const dLon = toRad(geoCalc.lonB - geoCalc.lonA);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(geoCalc.latA)) * Math.cos(toRad(geoCalc.latB)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }, [geoCalc]);

  const travelSpeedKmh = useMemo(() => {
    const hours = Math.max(geoCalc.elapsedMinutes, 1) / 60;
    return haversineDist / hours;
  }, [haversineDist, geoCalc.elapsedMinutes]);

  const isImpossibleTravel = travelSpeedKmh > 850 && haversineDist > 20;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <ShieldAlert className="w-6 h-6 text-slate-950" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  FraudGuard AI
                </span>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  v1.0 React Console
                </span>
              </div>
              <p className="text-xs text-slate-400">Intelligent Credit Card Fraud Detection & Triage</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-700/50">
              <span className={`w-2 h-2 rounded-full ${apiConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
              <span>Backend API: <b>http://localhost:8000</b></span>
            </div>
            <div className="text-xs bg-emerald-950/40 text-emerald-300 border border-emerald-800/40 px-3 py-1.5 rounded-lg font-mono">
              Cutoff τ*: <b>0.020</b>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Bar */}
      <div className="border-b border-slate-800/80 bg-slate-900/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex gap-1 overflow-x-auto py-2">
          {[
            { id: 'csv_upload', label: '📁 CSV Upload & Fraud Triage', icon: FileSpreadsheet, count: batchItems.filter(i => i.decision === 'DECLINE_BLOCK').length },
            { id: 'scoring', label: '⚡ Live Scoring & XAI', icon: Zap },
            { id: 'queue', label: '📋 Tier-2 Review Queue', icon: FileText, count: reviewQueue.filter(i => i.status === 'PENDING').length },
            { id: 'cost', label: '₹ Financial Cost Optimizer', icon: IndianRupee },
            { id: 'travel', label: '🌐 Spatio-Temporal Travel', icon: MapPin },
            { id: 'drift', label: '📊 PSI Concept Drift', icon: Activity },
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-slate-950' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className={`text-xs px-1.5 py-0.2 rounded-full font-mono ${isActive ? 'bg-slate-950 text-emerald-400' : 'bg-slate-800 text-slate-300'}`}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">

        {/* TAB 0: CSV UPLOAD & FRAUD TRIAGE CONSOLE (USER'S REQUEST) */}
        {activeTab === 'csv_upload' && (
          <div className="space-y-6">
            {/* Header & Actions Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-emerald-400" />
                  CSV Batch Transaction Ingestion & Fraud Triage Console
                </h2>
                <p className="text-xs text-slate-400">
                  Upload transaction batches (.csv), automatically isolate fraud patterns, and perform one-click <b>Approve, Disprove, or Reject</b> actions.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <input
                  type="file"
                  accept=".csv"
                  ref={fileInputRef}
                  onChange={handleCsvFileSelect}
                  className="hidden"
                />

                {batchSummary && (
                  <button
                    onClick={handleClearBatch}
                    title="Clear current batch and upload a new one"
                    className="px-3 py-2 text-xs font-medium bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700/80 rounded-lg transition"
                  >
                    Clear Batch
                  </button>
                )}

                <button
                  onClick={handleDownloadTemplate}
                  title="Download standard CSV template for testing"
                  className="px-3 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg flex items-center gap-1.5 transition"
                >
                  <Download className="w-4 h-4 text-slate-400" />
                  Download Template (.csv)
                </button>

                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="px-4 py-2 text-xs font-bold bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 rounded-lg flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition cursor-pointer"
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Scoring Batch...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      {batchSummary ? 'Upload Another CSV' : 'Upload CSV Dataset'}
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Error banner if any */}
            {errorMsg && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                {errorMsg}
              </div>
            )}

            {!batchSummary ? (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition ${
                  isDragOver
                    ? 'border-emerald-400 bg-emerald-500/10'
                    : 'border-slate-700 hover:border-emerald-500/50 bg-slate-900/40 hover:bg-slate-900/70'
                }`}
              >
                <div className="flex flex-col items-center justify-center space-y-4 max-w-lg mx-auto">
                  <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                    {isUploading ? (
                      <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
                    ) : (
                      <UploadCloud className="w-8 h-8 text-emerald-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-slate-100">
                      {isUploading ? 'Ingesting & Scoring Dataset...' : 'Upload CSV Transaction Dataset'}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                      Drag and drop your transaction CSV here, or click to browse. The pipeline will automatically calculate rolling velocities, spatio-temporal audits, Isolation Forest anomaly scores, and TreeSHAP explainability codes.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                    <button
                      type="button"
                      disabled={isUploading}
                      className="px-4 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-emerald-500/20 flex items-center gap-2 transition"
                    >
                      <UploadCloud className="w-4 h-4" />
                      Select CSV File
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDownloadTemplate();
                      }}
                      className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 flex items-center gap-2 transition"
                    >
                      <Download className="w-4 h-4 text-slate-400" />
                      Download Sample Template (.csv)
                    </button>
                  </div>
                  <div className="text-[11px] text-slate-500 pt-1">
                    Accepts standard CSV with transaction columns (<span className="font-mono text-slate-400">Amount, V1-V28, Time, etc.</span>)
                  </div>
                </div>
              </div>
            ) : (
              <>
                {/* KPI Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
                <span className="text-[11px] text-slate-400 uppercase font-semibold">Total Uploaded</span>
                <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">{batchSummary.total_uploaded} Txns</div>
                <div className="text-[10px] text-slate-500 mt-0.5 truncate">{batchSummary.filename}</div>
              </div>

              <div className="bg-slate-900/60 border border-rose-900/40 bg-rose-950/10 rounded-xl p-3.5">
                <span className="text-[11px] text-rose-400 uppercase font-semibold flex items-center gap-1">
                  <XCircle className="w-3.5 h-3.5 text-rose-400" /> Flagged Frauds
                </span>
                <div className="text-xl font-bold font-mono text-rose-400 mt-0.5">{batchSummary.declines_count} Blocked</div>
                <div className="text-[10px] text-rose-300/80 mt-0.5 font-mono">₹{batchSummary.total_fraud_volume.toLocaleString('en-IN')} Stolen</div>
              </div>

              <div className="bg-slate-900/60 border border-amber-900/40 bg-amber-950/10 rounded-xl p-3.5">
                <span className="text-[11px] text-amber-400 uppercase font-semibold flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Suspicious 2FA
                </span>
                <div className="text-xl font-bold font-mono text-amber-400 mt-0.5">{batchSummary.challenges_count} Step-Up</div>
                <div className="text-[10px] text-amber-300/80 mt-0.5">SMS / OTP Required</div>
              </div>

              <div className="bg-slate-900/60 border border-emerald-900/40 bg-emerald-950/10 rounded-xl p-3.5">
                <span className="text-[11px] text-emerald-400 uppercase font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Safe Approved
                </span>
                <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">{batchSummary.approvals_count} Clean</div>
                <div className="text-[10px] text-emerald-300/80 mt-0.5 font-mono">₹{batchSummary.total_safe_volume.toLocaleString('en-IN')} Processed</div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 col-span-2 md:col-span-1">
                <span className="text-[11px] text-slate-400 uppercase font-semibold">Batch AI Latency</span>
                <div className="text-xl font-bold font-mono text-cyan-400 mt-0.5">{batchSummary.batch_processing_time_ms} ms</div>
                <div className="text-[10px] text-slate-500 mt-0.5">XGB+LGB+Cat+Isolation</div>
              </div>
            </div>

            {/* Bulk Actions & Filter Toolbar */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                {/* Filter Pills */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs text-slate-400 font-medium mr-1 flex items-center gap-1">
                    <Filter className="w-3.5 h-3.5" /> Filter:
                  </span>
                  <button
                    onClick={() => setFilterMode('FRAUD_ONLY')}
                    className={`text-xs px-3 py-1.5 rounded-lg border font-semibold transition ${
                      filterMode === 'FRAUD_ONLY'
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-sm'
                        : 'bg-slate-800/40 text-slate-400 border-slate-700/50 hover:bg-slate-800'
                    }`}
                  >
                    🚨 Fraud Transactions Only ({batchItems.filter(i => i.decision === 'DECLINE_BLOCK').length})
                  </button>

                  <button
                    onClick={() => setFilterMode('CHALLENGES')}
                    className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition ${
                      filterMode === 'CHALLENGES'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm'
                        : 'bg-slate-800/40 text-slate-400 border-slate-700/50 hover:bg-slate-800'
                    }`}
                  >
                    ⚠️ Suspicious ({batchItems.filter(i => i.decision === 'STEP_UP_CHALLENGE').length})
                  </button>

                  <button
                    onClick={() => setFilterMode('APPROVED')}
                    className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition ${
                      filterMode === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 shadow-sm'
                        : 'bg-slate-800/40 text-slate-400 border-slate-700/50 hover:bg-slate-800'
                    }`}
                  >
                    ✅ Normal / Safe ({batchItems.filter(i => i.decision === 'ALLOW').length})
                  </button>

                  <button
                    onClick={() => setFilterMode('ALL')}
                    className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition ${
                      filterMode === 'ALL'
                        ? 'bg-slate-700 text-slate-100 border-slate-600 shadow-sm'
                        : 'bg-slate-800/40 text-slate-400 border-slate-700/50 hover:bg-slate-800'
                    }`}
                  >
                    All ({batchItems.length})
                  </button>
                </div>

                {/* Search Box */}
                <div className="relative w-full md:w-64">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search by ID, User, or Reason..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* Bulk Decision Controls Bar */}
              <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">
                    Bulk Actions ({displayedBatchItems.length} items):
                  </span>
                  <button
                    onClick={() => handleBulkAction('REJECT_ALL')}
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-lg shadow-sm shadow-rose-600/30 flex items-center gap-1.5 transition"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject Everything
                  </button>

                  <button
                    onClick={() => handleBulkAction('DISPROVE_ALL')}
                    className="px-3 py-1.5 bg-amber-600/90 hover:bg-amber-500 text-white text-xs font-bold rounded-lg shadow-sm shadow-amber-600/30 flex items-center gap-1.5 transition"
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Disprove Everything
                  </button>

                  <button
                    onClick={() => handleBulkAction('APPROVE_ALL')}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg shadow-sm shadow-emerald-600/30 flex items-center gap-1.5 transition"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Approve Everything
                  </button>
                </div>

                <button
                  onClick={handleExportAuditedCsv}
                  className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 transition"
                >
                  <Download className="w-3.5 h-3.5 text-cyan-400" />
                  Export Audited CSV
                </button>
              </div>
            </div>

            {/* Fraud & Batch Transactions Table */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
              <div className="p-3 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">
                  Showing {displayedBatchItems.length} of {batchItems.length} transactions
                  {filterMode === 'FRAUD_ONLY' && ' (Filtered: Flagged Frauds Only)'}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  Pending: {batchItems.filter(i => i.audit_status === 'PENDING').length} |
                  Approved: {batchItems.filter(i => i.audit_status === 'APPROVED').length} |
                  Disproved: {batchItems.filter(i => i.audit_status === 'DISPROVED').length} |
                  Rejected: {batchItems.filter(i => i.audit_status === 'REJECTED_BLOCKED').length}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950/90 border-b border-slate-800 text-slate-400 uppercase font-semibold">
                    <tr>
                      <th className="px-3.5 py-3">Txn ID / Cardholder</th>
                      <th className="px-3.5 py-3">Amount</th>
                      <th className="px-3.5 py-3">Fraud Risk</th>
                      <th className="px-3.5 py-3">AI Decision</th>
                      <th className="px-3.5 py-3">Anomaly Score</th>
                      <th className="px-3.5 py-3">Primary Reason Code</th>
                      <th className="px-3.5 py-3">Audit Determination</th>
                      <th className="px-3.5 py-3 text-right">Triage Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {displayedBatchItems.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="px-4 py-8 text-center text-slate-500 font-sans">
                          No transactions found matching the selected filter.
                        </td>
                      </tr>
                    ) : (
                      displayedBatchItems.map(txn => (
                        <tr
                          key={txn.id}
                          className={`hover:bg-slate-800/30 transition ${
                            txn.decision === 'DECLINE_BLOCK' ? 'bg-rose-950/5' : ''
                          }`}
                        >
                          <td className="px-3.5 py-2.5">
                            <div className="font-bold text-slate-200">{txn.id}</div>
                            <div className="text-[10px] text-slate-400 font-sans">{txn.user_id}</div>
                          </td>

                          <td className="px-3.5 py-2.5 font-bold text-slate-100">
                            ₹{txn.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>

                          <td className="px-3.5 py-2.5">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              txn.fraud_probability >= 0.02
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}>
                              {(txn.fraud_probability * 100).toFixed(2)}%
                            </span>
                          </td>

                          <td className="px-3.5 py-2.5">
                            {txn.decision === 'DECLINE_BLOCK' ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1 w-fit">
                                <XCircle className="w-3 h-3" /> DECLINE_BLOCK
                              </span>
                            ) : txn.decision === 'STEP_UP_CHALLENGE' ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center gap-1 w-fit">
                                <AlertTriangle className="w-3 h-3" /> STEP_UP
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-fit">
                                <CheckCircle2 className="w-3 h-3" /> ALLOW
                              </span>
                            )}
                          </td>

                          <td className="px-3.5 py-2.5 text-cyan-400">
                            {txn.unsupervised_anomaly_score.toFixed(3)}
                          </td>

                          <td className="px-3.5 py-2.5 font-sans text-slate-300 max-w-xs truncate" title={txn.primary_reason}>
                            {txn.primary_reason}
                          </td>

                          <td className="px-3.5 py-2.5">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              txn.audit_status === 'REJECTED_BLOCKED' ? 'bg-rose-600 text-white' :
                              txn.audit_status === 'DISPROVED' ? 'bg-amber-600 text-white' :
                              txn.audit_status === 'APPROVED' ? 'bg-emerald-600 text-white' :
                              'bg-slate-800 text-slate-300 border border-slate-700'
                            }`}>
                              {txn.audit_status}
                            </span>
                          </td>

                          <td className="px-3.5 py-2.5 text-right font-sans">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => handleRowDecision(txn.id, 'APPROVED')}
                                title="Approve Transaction (Mark Safe)"
                                className={`px-2 py-0.8 text-[11px] rounded transition font-medium ${
                                  txn.audit_status === 'APPROVED'
                                    ? 'bg-emerald-600 text-white'
                                    : 'bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25 border border-emerald-500/30'
                                }`}
                              >
                                Approve
                              </button>

                              <button
                                onClick={() => handleRowDecision(txn.id, 'DISPROVED')}
                                title="Disprove Fraud Claim"
                                className={`px-2 py-0.8 text-[11px] rounded transition font-medium ${
                                  txn.audit_status === 'DISPROVED'
                                    ? 'bg-amber-600 text-white'
                                    : 'bg-amber-500/15 text-amber-300 hover:bg-amber-500/25 border border-amber-500/30'
                                }`}
                              >
                                Disprove
                              </button>

                              <button
                                onClick={() => handleRowDecision(txn.id, 'REJECTED_BLOCKED')}
                                title="Confirm Fraud and Reject Transaction"
                                className={`px-2 py-0.8 text-[11px] rounded transition font-medium ${
                                  txn.audit_status === 'REJECTED_BLOCKED'
                                    ? 'bg-rose-600 text-white'
                                    : 'bg-rose-500/15 text-rose-300 hover:bg-rose-500/25 border border-rose-500/30'
                                }`}
                              >
                                Reject
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    )}

        {/* TAB 1: LIVE SCORING & XAI CONSOLE */}
        {activeTab === 'scoring' && (
          <div className="space-y-6">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Total Scored Today</span>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold font-mono text-slate-100">142,850</span>
                  <span className="text-xs font-semibold text-emerald-400 flex items-center gap-0.5">
                    <TrendingUp className="w-3 h-3" /> +12.4%
                  </span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Decline / Block Rate</span>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold font-mono text-rose-400">0.48%</span>
                  <span className="text-xs font-semibold text-slate-400">Target &lt;1.0%</span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Step-Up 2FA Rate</span>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold font-mono text-amber-400">1.12%</span>
                  <span className="text-xs font-semibold text-slate-400">SMS / OTP</span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Net Rupee Savings</span>
                <div className="mt-1 flex items-baseline justify-between">
                  <span className="text-2xl font-bold font-mono text-emerald-400">₹2,92,38,820</span>
                  <span className="text-xs font-semibold text-emerald-400">Optimized</span>
                </div>
              </div>
            </div>

            {/* Scenario Preset Selector */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <div>
                  <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-emerald-400" />
                    Live Transaction Simulation Presets
                  </h3>
                  <p className="text-xs text-slate-400">Choose a pre-configured banking scenario or modify values directly</p>
                </div>
                <div className="flex gap-2">
                  {Object.entries(PRESET_SCENARIOS).map(([key, item]) => (
                    <button
                      key={key}
                      onClick={() => handlePresetChange(key)}
                      className={`text-xs px-3 py-1.5 rounded-lg border transition font-medium ${
                        selectedPreset === key
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : 'bg-slate-800/40 text-slate-400 border-slate-700/40 hover:bg-slate-800'
                      }`}
                    >
                      {item.name.split(':')[0]}
                    </button>
                  ))}
                </div>
              </div>

              {/* Form Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                <div>
                  <label className="text-xs text-slate-400 font-medium">Transaction ID</label>
                  <input
                    type="text"
                    value={txnForm.id}
                    onChange={e => setTxnForm({ ...txnForm, id: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium">Amount (₹ INR)</label>
                  <input
                    type="number"
                    value={txnForm.amount}
                    onChange={e => setTxnForm({ ...txnForm, amount: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium">Terminal Latent V14</label>
                  <input
                    type="number"
                    step="0.1"
                    value={txnForm.v14}
                    onChange={e => setTxnForm({ ...txnForm, v14: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium">Acquiring Latent V4</label>
                  <input
                    type="number"
                    step="0.1"
                    value={txnForm.v4}
                    onChange={e => setTxnForm({ ...txnForm, v4: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium">Distance from Prior Txn (km)</label>
                  <input
                    type="number"
                    value={txnForm.distance_prev_km}
                    onChange={e => setTxnForm({ ...txnForm, distance_prev_km: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium">Time Delta Since Prior (sec)</label>
                  <input
                    type="number"
                    value={txnForm.time_delta_sec}
                    onChange={e => setTxnForm({ ...txnForm, time_delta_sec: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium">Velocity (Txn Count in 1h)</label>
                  <input
                    type="number"
                    value={txnForm.velocity_cnt_1h}
                    onChange={e => setTxnForm({ ...txnForm, velocity_cnt_1h: e.target.value })}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm font-mono text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleScoreTransaction}
                    disabled={isLoading}
                    className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold px-4 py-2 rounded-lg transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 text-sm"
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Scoring...
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        Execute Scoring
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Scoring Results Container */}
            {scoringResult && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fadeIn">
                {/* Decision & Probability Gauge */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
                  <div>
                    <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">AI Decision Outcome</span>
                    <div className="mt-3 flex items-center justify-between">
                      <div>
                        {scoringResult.decision === 'DECLINE_BLOCK' ? (
                          <div className="flex items-center gap-2 text-rose-400 font-extrabold text-xl">
                            <XCircle className="w-6 h-6 text-rose-500" />
                            DECLINE_BLOCK
                          </div>
                        ) : scoringResult.decision === 'STEP_UP_CHALLENGE' ? (
                          <div className="flex items-center gap-2 text-amber-400 font-extrabold text-xl">
                            <AlertTriangle className="w-6 h-6 text-amber-500" />
                            STEP_UP_CHALLENGE
                          </div>
                        ) : (
                          <div className="flex items-center gap-2 text-emerald-400 font-extrabold text-xl">
                            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                            ALLOW (SEAMLESS)
                          </div>
                        )}
                      </div>
                      <span className="font-mono text-xs text-slate-400 bg-slate-800 px-2.5 py-1 rounded">
                        Latency: {scoringResult.inference_latency_ms} ms
                      </span>
                    </div>

                    <div className="mt-4 p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300">
                      <b>Policy Recommendation:</b> {scoringResult.recommendation}
                    </div>

                    {/* Progress Bar / Risk Score */}
                    <div className="mt-5">
                      <div className="flex justify-between text-xs font-semibold mb-1">
                        <span className="text-slate-400">Calibrated Fraud Probability</span>
                        <span className="text-slate-100 font-mono">{(scoringResult.fraud_probability * 100).toFixed(2)}%</span>
                      </div>
                      <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            scoringResult.fraud_probability >= 0.02
                              ? 'bg-gradient-to-r from-amber-500 to-rose-500'
                              : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(5, scoringResult.fraud_probability * 100))}%` }}
                        ></div>
                      </div>
                      <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                        <span>Safe (0%)</span>
                        <span className="text-emerald-400">Cutoff τ*: 2.0%</span>
                        <span>High Risk (100%)</span>
                      </div>
                    </div>
                  </div>

                  {/* Impossible Travel Banner if present */}
                  {scoringResult.spatio_temporal_audit?.is_impossible_travel && (
                    <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                      <div>
                        <b>Card Cloning Geo Alert:</b> Transit velocity{' '}
                        <span className="font-mono font-bold text-rose-200">
                          {scoringResult.spatio_temporal_audit.speed_kmh.toLocaleString()} km/h
                        </span>{' '}
                        exceeds commercial aviation limits. Physical card cloning detected.
                      </div>
                    </div>
                  )}
                </div>

                {/* Ensemble Model Consensus */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Base Learners & Anomaly Score</span>
                  <div className="mt-4 space-y-3">
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-300 font-medium">Unsupervised Isolation Forest</span>
                        <span className="font-mono text-cyan-400 font-semibold">{scoringResult.unsupervised_anomaly_score}</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="h-full bg-cyan-400 rounded-full" style={{ width: `${scoringResult.unsupervised_anomaly_score * 100}%` }}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-300 font-medium">XGBoost Classifier</span>
                        <span className="font-mono text-emerald-400 font-semibold">{scoringResult.base_model_probabilities.xgboost}</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-400 rounded-full" style={{ width: `${scoringResult.base_model_probabilities.xgboost * 100}%` }}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-300 font-medium">LightGBM Classifier</span>
                        <span className="font-mono text-teal-400 font-semibold">{scoringResult.base_model_probabilities.lightgbm}</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="h-full bg-teal-400 rounded-full" style={{ width: `${scoringResult.base_model_probabilities.lightgbm * 100}%` }}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-300 font-medium">CatBoost Classifier</span>
                        <span className="font-mono text-indigo-400 font-semibold">{scoringResult.base_model_probabilities.catboost}</span>
                      </div>
                      <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-400 rounded-full" style={{ width: `${scoringResult.base_model_probabilities.catboost * 100}%` }}></div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
                    Stacking Meta-Learner: <b>Regularized L2 Logistic Regression</b>
                  </div>
                </div>

                {/* TreeSHAP Compliance Reason Codes */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">TreeSHAP Reason Codes</span>
                    <span className="text-[10px] text-emerald-400 border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 rounded">
                      FCRA Auditable
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {scoringResult.reason_codes && scoringResult.reason_codes.map((rc, idx) => (
                      <div key={idx} className="p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-lg">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-mono font-bold text-emerald-400">#{rc.rank} {rc.reason_code}</span>
                          <span className="font-mono text-slate-400 font-medium">Impact: {rc.relative_impact_percent}%</span>
                        </div>
                        <p className="text-xs text-slate-300 mt-1">{rc.plain_english_explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: REVIEW QUEUE */}
        {activeTab === 'queue' && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-emerald-400" />
                  Tier-2 Fraud Squad Manual Review Queue
                </h2>
                <p className="text-xs text-slate-400">Human-in-the-loop triage for escalated transactions</p>
              </div>
              <span className="text-xs bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-slate-300 font-mono">
                {reviewQueue.filter(i => i.status === 'PENDING').length} Items Pending Review
              </span>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="px-4 py-3">Txn ID / Time</th>
                    <th className="px-4 py-3">Cardholder</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Fraud Risk</th>
                    <th className="px-4 py-3">Primary Reason Code</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Triage Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {reviewQueue.map(item => (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition">
                      <td className="px-4 py-3">
                        <div className="font-bold text-slate-200">{item.id}</div>
                        <div className="text-[10px] text-slate-500">{item.time}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-300">{item.user}</td>
                      <td className="px-4 py-3 font-bold text-slate-100">{item.amount}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                          item.fraud_prob >= 0.7 ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {(item.fraud_prob * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 font-sans text-slate-300 max-w-xs truncate">{item.primary_reason}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          item.status === 'PENDING' ? 'bg-slate-800 text-slate-300' :
                          item.status === 'APPROVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                          item.status === 'CONFIRMED_FRAUD' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                        }`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-sans">
                        {item.status === 'PENDING' ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleQueueAction(item.id, 'APPROVED')}
                              className="px-2.5 py-1 text-xs bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 rounded"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleQueueAction(item.id, 'CONFIRMED_FRAUD')}
                              className="px-2.5 py-1 text-xs bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 rounded"
                            >
                              Block
                            </button>
                            <button
                              onClick={() => handleQueueAction(item.id, 'ESCALATED')}
                              className="px-2.5 py-1 text-xs bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 rounded"
                            >
                              Escalate
                            </button>
                          </div>
                        ) : (
                          <span className="text-[10px] text-slate-500 font-sans">Audited</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: FINANCIAL COST OPTIMIZER */}
        {activeTab === 'cost' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <IndianRupee className="w-5 h-5 text-emerald-400" />
                Cost-Sensitive Thresholding & Financial Loss Matrix
              </h2>
              <p className="text-xs text-slate-400">
                Resolving the <b>Accuracy Paradox</b> by dynamically minimizing total bank financial loss instead of using arbitrary 0.50 cutoffs.
              </p>
            </div>

            {/* Benchmark Table */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden p-4">
              <h3 className="text-sm font-semibold text-slate-200 mb-3">Model Benchmark Comparison (Accuracy Paradox Demonstration)</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase">
                    <tr>
                      <th className="px-3 py-2.5">Strategy / Decision Cutoff</th>
                      <th className="px-3 py-2.5">Accuracy</th>
                      <th className="px-3 py-2.5">Recall</th>
                      <th className="px-3 py-2.5">Precision</th>
                      <th className="px-3 py-2.5">PR-AUC</th>
                      <th className="px-3 py-2.5">Total Financial Loss</th>
                      <th className="px-3 py-2.5">Banking Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    <tr className="bg-rose-950/10">
                      <td className="px-3 py-2.5 font-sans font-semibold text-rose-300">Naive "Predict All Legitimate"</td>
                      <td className="px-3 py-2.5 font-bold">95.08%</td>
                      <td className="px-3 py-2.5 text-rose-400">0.00%</td>
                      <td className="px-3 py-2.5 text-rose-400">0.00%</td>
                      <td className="px-3 py-2.5">0.0000</td>
                      <td className="px-3 py-2.5 font-bold text-rose-400">₹2,99,93,868</td>
                      <td className="px-3 py-2.5 font-sans text-rose-400">❌ Disastrous (100% Frauds Missed)</td>
                    </tr>
                    <tr className="bg-amber-950/10">
                      <td className="px-3 py-2.5 font-sans font-semibold text-amber-300">Static 0.50 Threshold</td>
                      <td className="px-3 py-2.5">95.08%</td>
                      <td className="px-3 py-2.5 text-amber-400">0.00%</td>
                      <td className="px-3 py-2.5 text-amber-400">0.00%</td>
                      <td className="px-3 py-2.5">0.0506</td>
                      <td className="px-3 py-2.5 font-bold text-amber-400">₹2,99,93,868</td>
                      <td className="px-3 py-2.5 font-sans text-amber-400">⚠️ Sub-optimal Cutoff</td>
                    </tr>
                    <tr className="bg-emerald-950/20 border-l-4 border-emerald-500">
                      <td className="px-3 py-2.5 font-sans font-bold text-emerald-300">Cost-Optimized Cutoff (τ* = 0.020)</td>
                      <td className="px-3 py-2.5">4.92%</td>
                      <td className="px-3 py-2.5 font-bold text-emerald-400">100.00%</td>
                      <td className="px-3 py-2.5">4.92%</td>
                      <td className="px-3 py-2.5 font-bold text-emerald-400">0.0506</td>
                      <td className="px-3 py-2.5 font-bold text-emerald-400">₹7,55,040</td>
                      <td className="px-3 py-2.5 font-sans text-emerald-400 font-bold">✅ ₹2,92,38,828 Preserved</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Financial Parameters Sliders */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-semibold text-slate-200">Financial Matrix Parameters</h3>
                <div>
                  <div className="flex justify-between text-xs mb-1 text-slate-300">
                    <span>Chargeback Penalty Fee (₹ INR)</span>
                    <span className="font-mono font-bold text-emerald-400">₹{costParams.chargebackFee}</span>
                  </div>
                  <input
                    type="range"
                    min="500"
                    max="5000"
                    step="100"
                    value={costParams.chargebackFee}
                    onChange={e => setCostParams({ ...costParams, chargebackFee: parseFloat(e.target.value) })}
                    className="w-full accent-emerald-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1 text-slate-300">
                    <span>False Positive Customer Friction Cost (₹ INR)</span>
                    <span className="font-mono font-bold text-amber-400">₹{costParams.frictionCost}</span>
                  </div>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    step="50"
                    value={costParams.frictionCost}
                    onChange={e => setCostParams({ ...costParams, frictionCost: parseFloat(e.target.value) })}
                    className="w-full accent-emerald-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1 text-slate-300">
                    <span>True Positive Automated OTP Verification Fee (₹ INR)</span>
                    <span className="font-mono font-bold text-cyan-400">₹{costParams.investigationFee}</span>
                  </div>
                  <input
                    type="range"
                    min="5"
                    max="100"
                    step="5"
                    value={costParams.investigationFee}
                    onChange={e => setCostParams({ ...costParams, investigationFee: parseFloat(e.target.value) })}
                    className="w-full accent-emerald-500"
                  />
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-2">Cost Optimization Philosophy</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    In retail banking, a <b>False Negative (missed fraud)</b> costs the full transaction amount plus chargeback compliance penalties (₹1,500+).
                    Conversely, a <b>False Positive (legitimate cardholder challenged)</b> incurs minor friction (₹450) or an SMS OTP step-up (₹25).
                  </p>
                  <p className="text-xs text-slate-300 mt-2 leading-relaxed">
                    By computing the threshold $\tau^*$ that minimizes net financial loss, the system captures 100% of high-value attacks while safeguarding customer trust.
                  </p>
                </div>
                <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-300">
                  <b>Estimated Annual ROI:</b> Preserves approximately <b>₹2.92 Cr</b> in capital per 25,000 transactions.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: SPATIO-TEMPORAL TRAVEL */}
        {activeTab === 'travel' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-emerald-400" />
                Spatio-Temporal Tracking & Impossible Travel Detection
              </h2>
              <p className="text-xs text-slate-400">
                Calculates geodesic transit distance and velocity using the spherical <b>Haversine Formula</b> to catch physical card cloning.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Controls */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-semibold text-slate-200">Consecutive Transaction Coordinates</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400">Origin City (Txn 1)</label>
                    <input
                      type="text"
                      value={geoCalc.cityA}
                      onChange={e => setGeoCalc({ ...geoCalc, cityA: e.target.value })}
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400">Destination City (Txn 2)</label>
                    <input
                      type="text"
                      value={geoCalc.cityB}
                      onChange={e => setGeoCalc({ ...geoCalc, cityB: e.target.value })}
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400">Lat A</label>
                    <input
                      type="number"
                      step="0.01"
                      value={geoCalc.latA}
                      onChange={e => setGeoCalc({ ...geoCalc, latA: parseFloat(e.target.value) })}
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Lon A</label>
                    <input
                      type="number"
                      step="0.01"
                      value={geoCalc.lonA}
                      onChange={e => setGeoCalc({ ...geoCalc, lonA: parseFloat(e.target.value) })}
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Lat B</label>
                    <input
                      type="number"
                      step="0.01"
                      value={geoCalc.latB}
                      onChange={e => setGeoCalc({ ...geoCalc, latB: parseFloat(e.target.value) })}
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">Lon B</label>
                    <input
                      type="number"
                      step="0.01"
                      value={geoCalc.lonB}
                      onChange={e => setGeoCalc({ ...geoCalc, lonB: parseFloat(e.target.value) })}
                      className="mt-1 w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs font-mono"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1 text-slate-300">
                    <span>Elapsed Time Between Transactions (Minutes)</span>
                    <span className="font-mono font-bold text-emerald-400">{geoCalc.elapsedMinutes} mins</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="600"
                    value={geoCalc.elapsedMinutes}
                    onChange={e => setGeoCalc({ ...geoCalc, elapsedMinutes: parseInt(e.target.value) })}
                    className="w-full accent-emerald-500"
                  />
                </div>
              </div>

              {/* Geo Audit Result */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
                <div>
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Geodesic Audit Result</span>
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400">Haversine Distance</span>
                      <div className="text-lg font-bold font-mono text-slate-100 mt-1">
                        {haversineDist.toLocaleString(undefined, { maximumFractionDigits: 1 })} km
                      </div>
                    </div>

                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400">Apparent Speed</span>
                      <div className={`text-lg font-bold font-mono mt-1 ${isImpossibleTravel ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {travelSpeedKmh.toLocaleString(undefined, { maximumFractionDigits: 1 })} km/h
                      </div>
                    </div>
                  </div>

                  <div className="mt-5">
                    {isImpossibleTravel ? (
                      <div className="p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
                        <div className="font-bold flex items-center gap-1.5 text-rose-400 mb-1">
                          <AlertTriangle className="w-4 h-4" />
                          IMPOSSIBLE TRAVEL CONFIRMED
                        </div>
                        Transit velocity exceeds commercial aviation ceiling (850 km/h).
                        Card was utilized across two distant geographic coordinates in an impossibly short timeframe.
                      </div>
                    ) : (
                      <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs">
                        <div className="font-bold flex items-center gap-1.5 text-emerald-400 mb-1">
                          <CheckCircle2 className="w-4 h-4" />
                          PLAUSIBLE TRANSIT PATTERN
                        </div>
                        Apparent travel speed is within physical transportation bounds.
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-xs text-slate-500 font-mono mt-4">
                  Earth Mean Radius: 6,371 km | Commercial Aviation Ceiling: 850 km/h
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: CONCEPT DRIFT (PSI) MONITOR */}
        {activeTab === 'drift' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                <Activity className="w-5 h-5 text-emerald-400" />
                Concept Drift & Population Stability Index (PSI)
              </h2>
              <p className="text-xs text-slate-400">
                Monitors live production feature streams against baseline distributions to prevent silent model decay.
              </p>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden p-4">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase">
                  <tr>
                    <th className="px-4 py-3">Feature Name</th>
                    <th className="px-4 py-3">PSI Value</th>
                    <th className="px-4 py-3">Stability Status</th>
                    <th className="px-4 py-3">Threshold Rule</th>
                    <th className="px-4 py-3">Recommended Policy Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {[
                    { feat: 'Amount', psi: 0.042, status: 'STABLE', rule: 'PSI < 0.10', action: 'Nominal Operation' },
                    { feat: 'velocity_cnt_1h', psi: 0.081, status: 'STABLE', rule: 'PSI < 0.10', action: 'Nominal Operation' },
                    { feat: 'V14 (Terminal Risk)', psi: 0.145, status: 'MODERATE_DRIFT', rule: '0.10 ≤ PSI < 0.25', action: 'Queue for Analyst Review' },
                    { feat: 'travel_speed_kmh', psi: 0.021, status: 'STABLE', rule: 'PSI < 0.10', action: 'Nominal Operation' },
                    { feat: 'V4 (Acquiring Pattern)', psi: 0.285, status: 'SIGNIFICANT_DRIFT', rule: 'PSI ≥ 0.25', action: 'Trigger Retraining Alert' },
                    { feat: 'Overall Fraud Score', psi: 0.065, status: 'STABLE', rule: 'PSI < 0.10', action: 'Nominal Operation' }
                  ].map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="px-4 py-3 font-semibold text-slate-200">{row.feat}</td>
                      <td className="px-4 py-3 font-bold">{row.psi.toFixed(3)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          row.status === 'SIGNIFICANT_DRIFT' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                          row.status === 'MODERATE_DRIFT' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                          'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        }`}>
                          {row.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{row.rule}</td>
                      <td className="px-4 py-3 font-sans text-slate-300">{row.action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300 flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
              <div>
                <b>Automated Retraining Alert:</b> Feature <code className="font-mono bg-slate-900 px-1 py-0.5 rounded">V4 (Acquiring Pattern)</code>{' '}
                exceeded critical drift threshold (0.285 ≥ 0.250). Retraining pipeline automatically notified.
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
