import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  FolderOpen,
  ExternalLink,
  Settings,
  Sparkles,
  RefreshCw,
  Languages,
  Layers,
  XCircle,
  BookOpen,
  Plus,
  Trash2,
  Server,
  BookText,
  ChevronDown,
  ChevronUp,
  FileCode,
  Database,
  AlertTriangle,
} from "lucide-react";

interface TranslationProgress {
  value: number;
  page_progress?: number;
  current_page?: number;
  total_pages?: number;
  current_sentence?: number;
  total_sentences?: number;
  stage: string;
  message: string;
  fallback_info?: string | null;
  fallback_page?: number | null;
}

interface TranslationSuccess {
  mono?: string | null;
  dual?: string | null;
  docx?: string | null;
  filename: string;
  output_dir: string;
  export_format?: string;
  fallback_notice?: string | null;
}

export interface CustomModel {
  id: string;
  name: string;
}

export interface CustomProvider {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  models: CustomModel[];
}

const LANGUAGES = [
  { label: "Tiếng Việt (Vietnamese)", value: "vi" },
  { label: "Tiếng Anh (English)", value: "en" },
  { label: "Tiếng Trung Giản thể (Chinese)", value: "zh" },
  { label: "Tiếng Trung Phồn thể (Traditional Chinese)", value: "zh-TW" },
  { label: "Tiếng Nhật (Japanese)", value: "ja" },
  { label: "Tiếng Hàn (Korean)", value: "ko" },
  { label: "Tiếng Pháp (French)", value: "fr" },
  { label: "Tiếng Đức (German)", value: "de" },
  { label: "Tiếng Nga (Russian)", value: "ru" },
  { label: "Tiếng Tây Ban Nha (Spanish)", value: "es" },
];

const DEFAULT_SERVICES = [
  { id: "google", name: "Google Translate", desc: "Miễn phí, tốc độ cao, không cần API Key", badge: "Khuyên dùng" },
  { id: "marian", name: "MarianMT AI (Local Offline)", desc: "Mô hình dịch AI Helsinki-NLP siêu nhỏ gọn, chạy offline 100% trên máy", badge: "Local AI" },
  { id: "bing", name: "Bing Translate", desc: "Dịch vụ dịch thuật miễn phí từ Microsoft", badge: "Miễn phí" },
  { id: "openai:gpt-4o-mini", name: "OpenAI GPT-4o-mini", desc: "Dịch AI thông minh, cần OpenAI API Key", badge: "AI LLM" },
  { id: "deepseek:deepseek-chat", name: "DeepSeek-V3", desc: "Dịch tài liệu học thuật rất tốt, giá rẻ", badge: "AI LLM" },
  { id: "ollama:qwen2.5:7b", name: "Ollama (Offline)", desc: "Chạy mô hình AI cục bộ trên máy tính", badge: "Offline" },
  { id: "gemini:gemini-flash-lite-latest", name: "Google Gemini", desc: "Mô hình Gemini Flash thế hệ mới từ Google", badge: "AI LLM" },
];

export default function App() {
  const [filePath, setFilePath] = useState<string>("");
  const [fileName, setFileName] = useState<string>("");
  const [langIn, setLangIn] = useState<string>("en");
  const [langOut, setLangOut] = useState<string>("vi");
  const [service, setService] = useState<string>("google");
  const [pageChoice, setPageChoice] = useState<string>("all");
  const [customPages, setCustomPages] = useState<string>("");
  const [exportFormat, setExportFormat] = useState<string>("both");

  const [isTranslating, setIsTranslating] = useState<boolean>(false);
  const [overallProgress, setOverallProgress] = useState<number>(0);
  const [pageProgress, setPageProgress] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [currentStage, setCurrentStage] = useState<string>("init");
  const [progressMsg, setProgressMsg] = useState<string>("");

  const [result, setResult] = useState<TranslationSuccess | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [useCache, setUseCache] = useState<boolean>(true);

  // Standard API Keys
  const [openaiKey, setOpenaiKey] = useState<string>(localStorage.getItem("OPENAI_API_KEY") || "");
  const [deepseekKey, setDeepseekKey] = useState<string>(localStorage.getItem("DEEPSEEK_API_KEY") || "");
  const [geminiKey, setGeminiKey] = useState<string>(localStorage.getItem("GEMINI_API_KEY") || "");

  // AI Context & Glossary State
  const [customPrompt, setCustomPrompt] = useState<string>(() => localStorage.getItem("pdf2zh_custom_glossary") || "");
  const [showGlossaryInput, setShowGlossaryInput] = useState<boolean>(false);

  // Custom Providers State
  const [customProviders, setCustomProviders] = useState<CustomProvider[]>(() => {
    try {
      const saved = localStorage.getItem("pdf2zh_custom_providers");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Custom Provider Modal Form State
  const [showCustomModal, setShowCustomModal] = useState<boolean>(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [formProviderId, setFormProviderId] = useState<string>("");
  const [formDisplayName, setFormDisplayName] = useState<string>("");
  const [formBaseUrl, setFormBaseUrl] = useState<string>("");
  const [formApiKey, setFormApiKey] = useState<string>("");
  const [formModels, setFormModels] = useState<CustomModel[]>([{ id: "", name: "" }]);
  const [formError, setFormError] = useState<string>("");

  useEffect(() => {
    // Listen for drag & drop file events via Tauri Webview
    let unlistenDragDrop: (() => void) | undefined;
    try {
      getCurrentWebview().onDragDropEvent((event) => {
        if (event.payload.type === "drop") {
          setIsDragging(false);
          const paths = event.payload.paths;
          if (paths && paths.length > 0) {
            const selected = paths[0];
            const ext = selected.split(".").pop()?.toLowerCase();
            if (ext === "pdf" || ext === "doc" || ext === "docx") {
              setFilePath(selected);
              const name = selected.split(/[/\\]/).pop() || selected;
              setFileName(name);
              setResult(null);
              setErrorMsg("");
            } else {
              setErrorMsg("Vui lòng chỉ kéo thả tệp tài liệu PDF hoặc Word (.docx)!");
            }
          }
        } else if (event.payload.type === "enter" || event.payload.type === "over") {
          setIsDragging(true);
        } else if (event.payload.type === "leave") {
          setIsDragging(false);
        }
      }).then((unlisten) => {
        unlistenDragDrop = unlisten;
      });
    } catch (e) {
      console.warn("Drag & drop listener error:", e);
    }

    // Listen for real-time IPC events from Rust
    const unlistenProgress = listen<TranslationProgress>("translation-progress", (event) => {
      const newOverall = Math.round(event.payload.value * 100);
      setOverallProgress((prev) => Math.max(prev, newOverall));

      if (event.payload.page_progress !== undefined) {
        setPageProgress(Math.round(event.payload.page_progress * 100));
      }
      if (event.payload.current_page !== undefined) {
        setCurrentPage(Math.max(1, event.payload.current_page));
      }
      if (event.payload.total_pages !== undefined) {
        setTotalPages(Math.max(1, event.payload.total_pages));
      }
      if (event.payload.stage) {
        setCurrentStage(event.payload.stage);
      }
      if (event.payload.fallback_info !== undefined) {
        setFallbackNotice(event.payload.fallback_info || null);
      }
      setProgressMsg(event.payload.message || "Đang xử lý...");
    });

    const unlistenSuccess = listen<TranslationSuccess>("translation-success", (event) => {
      setIsTranslating(false);
      setOverallProgress(100);
      setPageProgress(100);
      setCurrentStage("done");
      setProgressMsg("Dịch tài liệu thành công!");
      if (event.payload.fallback_notice !== undefined) {
        setFallbackNotice(event.payload.fallback_notice || null);
      }
      setResult(event.payload);
    });

    const unlistenError = listen<{ message: string }>("translation-error", (event) => {
      setIsTranslating(false);
      setErrorMsg(event.payload.message || "Có lỗi phát sinh trong quá trình dịch.");
    });

    return () => {
      unlistenProgress.then((f) => f());
      unlistenSuccess.then((f) => f());
      unlistenError.then((f) => f());
      if (unlistenDragDrop) unlistenDragDrop();
    };
  }, []);

  const saveCustomProvidersToStorage = (providers: CustomProvider[]) => {
    setCustomProviders(providers);
    localStorage.setItem("pdf2zh_custom_providers", JSON.stringify(providers));
  };

  const openNewCustomProviderModal = () => {
    setEditingProviderId(null);
    setFormProviderId("");
    setFormDisplayName("");
    setFormBaseUrl("");
    setFormApiKey("");
    setFormModels([{ id: "", name: "" }]);
    setFormError("");
    setShowCustomModal(true);
  };

  const openEditCustomProviderModal = (provider: CustomProvider) => {
    setEditingProviderId(provider.id);
    setFormProviderId(provider.id);
    setFormDisplayName(provider.name);
    setFormBaseUrl(provider.baseUrl);
    setFormApiKey(provider.apiKey);
    setFormModels(provider.models.length > 0 ? [...provider.models] : [{ id: "", name: "" }]);
    setFormError("");
    setShowCustomModal(true);
  };

  const handleSaveCustomProvider = () => {
    const cleanId = formProviderId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "");
    if (!cleanId) {
      setFormError("Vui lòng nhập Provider ID hợp lệ (chữ thường, số, dấu gạch ngang/dưới)");
      return;
    }
    if (!formBaseUrl.trim()) {
      setFormError("Vui lòng nhập Base URL (ví dụ: https://api.myprovider.com/v1)");
      return;
    }

    const validModels = formModels
      .map((m) => ({ id: m.id.trim(), name: m.name.trim() || m.id.trim() }))
      .filter((m) => m.id.length > 0);

    if (validModels.length === 0) {
      setFormError("Vui lòng thêm ít nhất một Model ID (ví dụ: gpt-4o, deepseek-chat)");
      return;
    }

    const newProvider: CustomProvider = {
      id: cleanId,
      name: formDisplayName.trim() || cleanId,
      baseUrl: formBaseUrl.trim(),
      apiKey: formApiKey.trim(),
      models: validModels,
    };

    let updated: CustomProvider[];
    if (editingProviderId) {
      updated = customProviders.map((p) => (p.id === editingProviderId ? newProvider : p));
    } else {
      updated = [...customProviders.filter((p) => p.id !== cleanId), newProvider];
    }

    saveCustomProvidersToStorage(updated);
    // Automatically select the first model of this custom provider
    setService(`custom:${newProvider.id}:${validModels[0].id}`);
    setShowCustomModal(false);
  };

  const handleDeleteCustomProvider = (id: string) => {
    const updated = customProviders.filter((p) => p.id !== id);
    saveCustomProvidersToStorage(updated);
    if (service.startsWith(`custom:${id}:`)) {
      setService("google");
    }
    setShowCustomModal(false);
  };

  const handleDeleteModelFromProvider = (providerId: string, modelId: string) => {
    const updated = customProviders.map((p) => {
      if (p.id === providerId) {
        return {
          ...p,
          models: p.models.filter((m) => m.id !== modelId),
        };
      }
      return p;
    });
    saveCustomProvidersToStorage(updated);
    if (service === `custom:${providerId}:${modelId}`) {
      const remainingModels = updated.find((p) => p.id === providerId)?.models;
      if (remainingModels && remainingModels.length > 0) {
        setService(`custom:${providerId}:${remainingModels[0].id}`);
      } else {
        setService("google");
      }
    }
  };

  const handleSelectFile = async () => {
    try {
      const selected = await openDialog({
        multiple: false,
        filters: [{ name: "PDF Documents", extensions: ["pdf", "doc", "docx"] }],
      });
      if (selected && typeof selected === "string") {
        setFilePath(selected);
        const name = selected.split(/[/\\]/).pop() || selected;
        setFileName(name);
        setResult(null);
        setErrorMsg("");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartTranslation = async () => {
    if (!filePath) {
      setErrorMsg("Vui lòng chọn một tệp PDF cần dịch!");
      return;
    }

    setIsTranslating(true);
    setOverallProgress(5);
    setPageProgress(0);
    setCurrentPage(1);
    setTotalPages(1);
    setCurrentStage("init");
    setProgressMsg("Đang chuẩn bị tiến trình dịch...");
    setResult(null);
    setErrorMsg("");
    setFallbackNotice(null);

    let pages: number[] | null = null;
    if (pageChoice === "first") pages = [0];
    else if (pageChoice === "first5") pages = [0, 1, 2, 3, 4];
    else if (pageChoice === "custom" && customPages) {
      const list: number[] = [];
      customPages.split(",").forEach((part) => {
        const p = part.trim();
        if (p.includes("-")) {
          const [start, end] = p.split("-").map((n) => parseInt(n) - 1);
          for (let i = start; i <= end; i++) list.push(i);
        } else {
          list.push(parseInt(p) - 1);
        }
      });
      pages = list;
    }

    const envs: Record<string, string> = {};
    if (openaiKey) envs["OPENAI_API_KEY"] = openaiKey;
    if (deepseekKey) envs["DEEPSEEK_API_KEY"] = deepseekKey;
    if (geminiKey) envs["GEMINI_API_KEY"] = geminiKey;

    let targetService = service;

    // Handle Custom OpenAI-compatible Provider
    if (service.startsWith("custom:")) {
      const parts = service.split(":");
      const provId = parts[1];
      const modelId = parts.slice(2).join(":");
      const provider = customProviders.find((p) => p.id === provId);

      if (provider) {
        targetService = `openailiked:${modelId}`;
        envs["OPENAILIKED_BASE_URL"] = provider.baseUrl;
        envs["OPENAILIKED_API_KEY"] = provider.apiKey || "openailiked";
        envs["OPENAILIKED_MODEL"] = modelId;
      }
    }

    try {
      if (customPrompt.trim()) {
        localStorage.setItem("pdf2zh_custom_glossary", customPrompt.trim());
      }
      await invoke("start_translation", {
        params: {
          file: filePath,
          lang_in: langIn,
          lang_out: langOut,
          service: targetService,
          pages: pages,
          output_dir: null,
          envs: envs,
          prompt: customPrompt.trim() ? customPrompt.trim() : null,
          thread: 4,
          export_format: exportFormat,
          ignore_cache: !useCache,
        },
      });
    } catch (err: any) {
      setIsTranslating(false);
      setErrorMsg(String(err));
    }
  };

  const handleCancelTranslation = async () => {
    try {
      await invoke("cancel_translation");
      setIsTranslating(false);
      setProgressMsg("Đã hủy tiến trình dịch.");
    } catch (e) {
      console.error(e);
    }
  };

  const handleOpenFile = (path: string) => {
    invoke("open_file", { path });
  };

  const handleOpenExplorer = (path: string) => {
    invoke("open_in_explorer", { path });
  };

  const handleSaveSettings = () => {
    localStorage.setItem("OPENAI_API_KEY", openaiKey);
    localStorage.setItem("DEEPSEEK_API_KEY", deepseekKey);
    localStorage.setItem("GEMINI_API_KEY", geminiKey);
    setShowSettings(false);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 select-none overflow-hidden font-sans">
      {/* Header Bar */}
      <header className="h-14 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-slate-100 tracking-wide flex items-center gap-2">
              PDFMathTranslate Desktop
            </h1>
            <p className="text-[11px] text-slate-400">Dịch thuật PDF bảo toàn công thức toán & bố cục</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-950/40 border border-emerald-800/50 rounded-full text-[11px] text-emerald-400 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            IPC Native Core • Times New Roman
          </div>

          <button
            onClick={openNewCustomProviderModal}
            className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-amber-300 border border-slate-700/50 transition flex items-center gap-1.5 text-xs px-3"
            title="Thêm Custom Provider (OpenAI Compatible)"
          >
            <Server className="w-3.5 h-3.5 text-amber-400" />
            <span>Quản lý Custom API</span>
          </button>

          <button
            onClick={() => setShowSettings(true)}
            className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700/50 transition"
            title="Cài đặt API Keys"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 grid grid-cols-12 gap-6 p-6 overflow-hidden">
        {/* Left Column: File Input & Configuration */}
        <section className="col-span-5 flex flex-col gap-4 overflow-y-auto pr-1">
          {/* File Upload Box */}
          <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-5 shadow-xl space-y-4">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" />
              <span>Tài liệu đầu vào</span>
            </h2>

            <div
              onClick={!isTranslating ? handleSelectFile : undefined}
              className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition duration-200 ${
                isDragging
                  ? "border-emerald-400 bg-emerald-950/40 shadow-xl shadow-emerald-500/20 scale-[1.01]"
                  : filePath
                  ? "border-blue-500/50 bg-blue-950/20"
                  : "border-slate-800 hover:border-slate-700 bg-slate-950/40 hover:bg-slate-950/70"
              } ${isTranslating ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              <UploadCloud
                className={`w-9 h-9 mb-2 transition duration-300 ${
                  isDragging
                    ? "text-emerald-400 animate-bounce scale-110"
                    : "text-blue-400/80"
                }`}
              />
              {isDragging ? (
                <div className="space-y-1">
                  <p className="text-sm font-bold text-emerald-300">Thả tệp PDF vào đây để chọn</p>
                  <p className="text-xs text-emerald-400/80">Tự động nhận diện tài liệu ngay lập tức</p>
                </div>
              ) : filePath ? (
                <div className="space-y-1 max-w-full overflow-hidden">
                  <p className="text-xs font-semibold text-blue-300 truncate px-2">{fileName}</p>
                  <p className="text-[10px] text-slate-500 truncate">{filePath}</p>
                </div>
              ) : (
                <>
                  <p className="text-sm font-medium text-slate-300">Nhấp hoặc Kéo thả tệp PDF vào đây</p>
                  <p className="text-xs text-slate-500 mt-1">Hỗ trợ PDF bài báo khoa học, giáo trình, sách toán</p>
                </>
              )}
            </div>
          </div>

          {/* Translation Options */}
          <div className="bg-slate-900/70 border border-slate-800/90 rounded-2xl p-5 shadow-xl space-y-4">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Languages className="w-4 h-4 text-indigo-400" />
              <span>Cấu hình dịch thuật</span>
            </h2>

            {/* Language Selector */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Dịch từ</label>
                <select
                  disabled={isTranslating}
                  value={langIn}
                  onChange={(e) => setLangIn(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Dịch sang</label>
                <select
                  disabled={isTranslating}
                  value={langOut}
                  onChange={(e) => setLangOut(e.target.value)}
                  className="w-full bg-slate-950 border border-blue-500/40 rounded-xl px-3 py-2 text-xs text-blue-200 font-medium focus:outline-none focus:border-blue-500"
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Service Selector */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs text-slate-400 block">Dịch vụ dịch thuật (Engine)</label>
                <button
                  type="button"
                  onClick={openNewCustomProviderModal}
                  className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center gap-1 font-medium"
                >
                  <Plus className="w-3 h-3" />
                  <span>+ Thêm Custom API</span>
                </button>
              </div>

              <select
                disabled={isTranslating}
                value={service}
                onChange={(e) => setService(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-medium"
              >
                <optgroup label="✨ Miễn phí & Offline">
                  {DEFAULT_SERVICES.slice(0, 3).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} [{s.badge}] - {s.desc}
                    </option>
                  ))}
                </optgroup>

                <optgroup label="🤖 AI LLM Model">
                  {DEFAULT_SERVICES.slice(3).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} [{s.badge}] - {s.desc}
                    </option>
                  ))}
                </optgroup>

                {customProviders.length > 0 && (
                  <optgroup label="⚡ Custom Providers (OpenAI-compatible)">
                    {customProviders.map((cp) =>
                      cp.models.map((m) => (
                        <option key={`custom:${cp.id}:${m.id}`} value={`custom:${cp.id}:${m.id}`}>
                          [{cp.name}] {m.name || m.id} ({m.id})
                        </option>
                      ))
                    )}
                  </optgroup>
                )}
              </select>

              {/* Enhanced Custom Providers List with Quick Add Model & Delete */}
              {customProviders.length > 0 && (
                <div className="space-y-2 mt-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-amber-400" />
                      <span>Custom API đã lưu ({customProviders.length})</span>
                    </span>
                    <span className="text-[10px] text-slate-500">Nhấp model để chọn dịch</span>
                  </div>

                  <div className="space-y-2 pt-1">
                    {customProviders.map((cp) => (
                      <div
                        key={cp.id}
                        className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800/80 flex flex-col gap-2 hover:border-slate-700 transition"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs text-slate-200">{cp.name}</span>
                            <span className="text-[10px] text-slate-500 font-mono">({cp.id})</span>
                            <span className="px-1.5 py-0.2 text-[10px] rounded-md bg-blue-950/60 text-blue-400 border border-blue-800/40">
                              {cp.models.length} model{cp.models.length > 1 ? "s" : ""}
                            </span>
                          </div>

                          <div className="flex items-center gap-1">
                            <button
                              type="button"
                              onClick={() => openEditCustomProviderModal(cp)}
                              className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-300 hover:text-blue-200 text-[11px] flex items-center gap-1 transition"
                              title="Thêm Model hoặc chỉnh sửa API"
                            >
                              <Plus className="w-3 h-3 text-blue-400" />
                              <span>Thêm Model / Sửa</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                if (confirm(`Bạn có chắc chắn muốn xóa toàn bộ API Provider "${cp.name}" (${cp.id}) không?`)) {
                                  handleDeleteCustomProvider(cp.id);
                                }
                              }}
                              className="p-1.5 rounded-lg bg-rose-950/30 hover:bg-rose-900/50 text-rose-400 hover:text-rose-300 border border-rose-900/40 transition"
                              title="Xóa toàn bộ API Provider này"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                        {/* Model badges */}
                        <div className="flex flex-wrap gap-1">
                          {cp.models.map((m) => {
                            const isSelected = service === `custom:${cp.id}:${m.id}`;
                            return (
                              <div
                                key={m.id}
                                className={`group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono border transition ${
                                  isSelected
                                    ? "bg-blue-600/30 border-blue-500 text-blue-200 font-semibold shadow-sm shadow-blue-500/20"
                                    : "bg-slate-950 border-slate-800/80 text-slate-400 hover:border-slate-700 hover:text-slate-200 cursor-pointer"
                                }`}
                              >
                                <button
                                  type="button"
                                  onClick={() => setService(`custom:${cp.id}:${m.id}`)}
                                  className="text-left flex items-center gap-1"
                                >
                                  {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>}
                                  <span>{m.name || m.id}</span>
                                </button>
                                {cp.models.length > 1 && (
                                  <button
                                    type="button"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (confirm(`Bạn có chắc chắn muốn xóa model "${m.name || m.id}" khỏi ${cp.name}?`)) {
                                        handleDeleteModelFromProvider(cp.id, m.id);
                                      }
                                    }}
                                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 transition ml-0.5"
                                    title="Xóa model này"
                                  >
                                    <Trash2 className="w-2.5 h-2.5" />
                                  </button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Page Range Selector */}
            <div>
              <label className="text-xs text-slate-400 block mb-1">Phạm vi trang cần dịch</label>
              <div className="grid grid-cols-4 gap-2">
                {[
                  { id: "all", label: "Tất cả" },
                  { id: "first", label: "Trang 1" },
                  { id: "first5", label: "5 trang đầu" },
                  { id: "custom", label: "Tùy chọn" },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    disabled={isTranslating}
                    onClick={() => setPageChoice(opt.id)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-medium border transition ${
                      pageChoice === opt.id
                        ? "bg-blue-600/20 border-blue-500 text-blue-300"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
              {pageChoice === "custom" && (
                <div className="mt-2">
                  <input
                    type="text"
                    disabled={isTranslating}
                    value={customPages}
                    onChange={(e) => setCustomPages(e.target.value)}
                    placeholder="Ví dụ: 1-5, 8, 10-12"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">Hệ thống sẽ chỉ xuất file đúng với các trang bạn chọn.</p>
                </div>
              )}
            </div>

            {/* Output Format Selector */}
            <div>
              <label className="text-xs text-slate-400 block mb-1">Định dạng file xuất</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "both", label: "PDF + Word (.docx)" },
                  { id: "pdf", label: "Chỉ PDF (.pdf)" },
                  { id: "docx", label: "Chỉ Word (.docx)" },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    disabled={isTranslating}
                    onClick={() => setExportFormat(opt.id)}
                    className={`py-1.5 px-1 rounded-lg text-xs font-medium border text-center transition ${
                      exportFormat === opt.id
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-300"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* AI Context & Glossary Accordion */}
            <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 overflow-hidden">
              <button
                type="button"
                onClick={() => setShowGlossaryInput(!showGlossaryInput)}
                className="w-full p-3 flex items-center justify-between text-left hover:bg-slate-900/40 transition"
              >
                <div className="flex items-center gap-2">
                  <BookText className="w-4 h-4 text-amber-400" />
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">
                      Ngữ cảnh & Thuật ngữ AI
                    </span>
                    <span className="text-[10px] text-slate-500">
                      Tự động học ngữ cảnh & đồng nhất từ vựng cho sách dày 50+ trang
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-800/40 text-[10px] text-emerald-400 font-medium">
                    Auto-Context ON
                  </span>
                  {showGlossaryInput ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {showGlossaryInput && (
                <div className="p-3 border-t border-slate-800/60 space-y-2 bg-slate-950/90">
                  <label className="text-[11px] text-slate-300 font-medium block">
                    Bảng thuật ngữ / Chỉ dẫn dịch thuật riêng (Tùy chọn)
                  </label>
                  <textarea
                    rows={4}
                    disabled={isTranslating}
                    value={customPrompt}
                    onChange={(e) => setCustomPrompt(e.target.value)}
                    placeholder={"Nhập các từ điển thuật ngữ hoặc phong cách dịch:\n- malware: phần mềm độc hại\n- pipeline: chu trình xử lý\n- encoder: bộ mã hóa\n- Dịch theo văn phong học thuật Việt Nam chuẩn mực."}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono resize-none"
                  ></textarea>
                  <p className="text-[10px] text-slate-500">
                    AI sẽ tự động đọc ngữ cảnh tài liệu và áp dụng bảng từ điển này xuyên suốt từ trang đầu đến trang cuối.
                  </p>
                </div>
              )}
            </div>

            {/* Translation Memory (SQLite Cache) Switch */}
            <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-2xl flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-emerald-950/50 border border-emerald-800/30 text-emerald-400">
                  <Database className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-200">
                      Bộ nhớ đệm (Translation Memory)
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                      SQLite
                    </span>
                  </div>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    Lưu câu đã dịch, dịch lại siêu tốc & không tốn phí API
                  </span>
                </div>
              </div>
              <button
                type="button"
                disabled={isTranslating}
                onClick={() => setUseCache(!useCache)}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none ${
                  useCache ? "bg-emerald-500" : "bg-slate-700"
                } ${isTranslating ? "opacity-60 cursor-not-allowed" : ""}`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    useCache ? "translate-x-4" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            {/* Action Buttons */}
            <div className="pt-2">
              {isTranslating ? (
                <button
                  type="button"
                  onClick={handleCancelTranslation}
                  className="w-full py-2.5 px-4 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 text-xs font-semibold flex items-center justify-center gap-2 transition"
                >
                  <XCircle className="w-4 h-4 text-rose-400" />
                  <span>Hủy tiến trình</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleStartTranslation}
                  disabled={!filePath}
                  className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg transition ${
                    filePath
                      ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/25"
                      : "bg-slate-800/50 text-slate-500 cursor-not-allowed border border-slate-800"
                  }`}
                >
                  <Layers className="w-4 h-4" />
                  <span>Bắt đầu Dịch PDF</span>
                </button>
              )}
            </div>

            {errorMsg && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}
          </div>
        </section>

        {/* Right Column: Status, Progress & Output Results */}
        <section className="col-span-7 flex flex-col gap-4 overflow-hidden">
          {/* Dual Progress / Status Card */}
          {isTranslating && (
            <div className="bg-slate-900/90 border border-blue-500/40 rounded-2xl p-5 shadow-2xl space-y-4 animate-fade-in">
              {/* Header / Status Text */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
                  <span className="font-semibold text-sm text-slate-200">{progressMsg}</span>
                </div>
                <div className="flex items-center gap-2">
                  {totalPages > 1 && (
                    <span className="text-xs px-2.5 py-0.5 rounded-md bg-slate-800/80 text-slate-300 font-mono border border-slate-700/50">
                      Trang {currentPage}/{totalPages}
                    </span>
                  )}
                  <span className="text-base font-bold text-blue-400 font-mono">{overallProgress}%</span>
                </div>
              </div>

              {/* Dynamic Fallback Notice Banner */}
              {fallbackNotice && (
                <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-amber-950/70 border border-amber-500/50 text-amber-200 text-xs shadow-md shadow-amber-950/40 animate-fade-in">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span className="font-medium leading-relaxed">{fallbackNotice}</span>
                </div>
              )}

              {/* Primary Progress Bar: Overall Document Progress */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px] text-slate-400">
                  <span className="font-medium text-slate-300">Tiến độ toàn bộ tài liệu (gồm cả 3 giai đoạn)</span>
                  <span className="font-bold text-blue-300 font-mono">{overallProgress}%</span>
                </div>
                <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden border border-slate-800 p-0.5">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500 transition-all duration-300 rounded-full shadow-sm shadow-blue-500/30"
                    style={{ width: `${overallProgress}%` }}
                  ></div>
                </div>
              </div>

              {/* Secondary Progress Bar: Current Page Detail Progress */}
              <div className="space-y-1 pt-0.5">
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Chi tiết công việc Trang {currentPage}{totalPages > 1 ? `/${totalPages}` : ""}</span>
                  <span className="font-mono text-indigo-300 font-medium">{pageProgress}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800/80">
                  <div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300 rounded-full"
                    style={{ width: `${pageProgress}%` }}
                  ></div>
                </div>
              </div>

              {/* Step indicator */}
              <div className="grid grid-cols-3 gap-2 pt-1 text-[11px] text-center font-medium">
                <div
                  className={`p-2 rounded-xl border transition-all duration-300 ${
                    currentStage === "layout" || overallProgress > 0
                      ? "border-blue-500/60 bg-blue-950/40 text-blue-300 shadow-sm shadow-blue-500/20"
                      : "border-slate-800 text-slate-600 bg-slate-950/50"
                  }`}
                >
                  1. Phân tích Layout AI
                </div>
                <div
                  className={`p-2 rounded-xl border transition-all duration-300 ${
                    currentStage === "translating" || (overallProgress >= 5 && overallProgress < 90)
                      ? "border-indigo-500/60 bg-indigo-950/40 text-indigo-300 shadow-sm shadow-indigo-500/20"
                      : "border-slate-800 text-slate-600 bg-slate-950/50"
                  }`}
                >
                  2. Dịch & Giữ công thức
                </div>
                <div
                  className={`p-2 rounded-xl border transition-all duration-300 ${
                    currentStage === "rendering" || overallProgress >= 90
                      ? "border-emerald-500/60 bg-emerald-950/40 text-emerald-300 shadow-sm shadow-emerald-500/20"
                      : "border-slate-800 text-slate-600 bg-slate-950/50"
                  }`}
                >
                  {exportFormat === "docx"
                    ? "3. Xuất file Word (.docx)"
                    : exportFormat === "pdf"
                    ? "3. Xuất PDF Times New Roman"
                    : "3. Xuất PDF & Word (.docx)"}
                </div>
              </div>
            </div>
          )}

          {/* Results Output View */}
          {result ? (
            <div className="flex-1 bg-slate-900/70 border border-emerald-500/30 rounded-2xl p-6 shadow-xl flex flex-col justify-between overflow-y-auto">
              <div>
                <div className="flex items-center gap-3 mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <CheckCircle2 className="w-7 h-7 text-emerald-400 shrink-0" />
                  <div>
                    <h3 className="text-base font-bold text-emerald-300">Dịch thuật hoàn tất xuất sắc!</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Tài liệu đã được xuất ra với định dạng font Times New Roman chuẩn mực.</p>
                  </div>
                </div>

                {/* Fallback Notice on Result Card */}
                {(result.fallback_notice || fallbackNotice) && (
                  <div className="flex items-start gap-2.5 mb-5 p-3.5 rounded-xl bg-amber-950/50 border border-amber-600/60 text-amber-200 text-xs shadow-md">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                    <div>
                      <span className="font-bold text-amber-300">Ghi chú chuyển giao bộ dịch: </span>
                      <span>{result.fallback_notice || fallbackNotice}</span>
                    </div>
                  </div>
                )}

                <div className="space-y-4">
                  {/* Mono File Card - only when PDF or both requested */}
                  {result.mono && (result.export_format || exportFormat) !== "docx" && (
                    <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileText className="w-5 h-5 text-blue-400" />
                          <div>
                            <h4 className="text-sm font-semibold text-slate-200">Bản dịch Đơn ngữ (Mono PDF)</h4>
                            <p className="text-[11px] text-slate-400">Chỉ chứa toàn bộ nội dung tiếng Việt đã dịch</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleOpenFile(result.mono!)}
                          className="flex-1 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Mở đọc Đơn ngữ</span>
                        </button>
                        <button
                          onClick={() => handleOpenExplorer(result.mono!)}
                          className="py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 border border-slate-700 transition"
                        >
                          <FolderOpen className="w-3.5 h-3.5" />
                          <span>Mở thư mục</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Word (.docx) File Card - only when Word or both requested */}
                  {result.docx && (result.export_format || exportFormat) !== "pdf" && (
                    <div className="p-4 rounded-xl bg-blue-950/25 border border-blue-700/60 hover:border-blue-600 transition shadow-lg shadow-blue-950/30">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <FileCode className="w-5 h-5 text-blue-400" />
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-sm font-bold text-blue-200">Bản dịch Microsoft Word (.docx)</h4>
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-900/80 text-blue-300 font-medium border border-blue-600/50">
                                Dễ biên tập & in ấn
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400">Định dạng Times New Roman, dễ dàng chỉnh sửa câu chữ và công thức</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleOpenFile(result.docx!)}
                          className="flex-1 py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Mở file Word (.docx)</span>
                        </button>
                        <button
                          onClick={() => handleOpenExplorer(result.docx!)}
                          className="py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 border border-slate-700 transition"
                        >
                          <FolderOpen className="w-3.5 h-3.5" />
                          <span>Mở thư mục</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Dual File Card - only when PDF or both requested */}
                  {result.dual && (result.export_format || exportFormat) !== "docx" && (
                    <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <BookOpen className="w-5 h-5 text-indigo-400" />
                          <div>
                            <h4 className="text-sm font-semibold text-slate-200">Bản dịch Song ngữ (Dual PDF)</h4>
                            <p className="text-[11px] text-slate-400">Trang gốc và trang dịch xen kẽ để dễ đối chiếu</p>
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleOpenFile(result.dual!)}
                          className="flex-1 py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Mở đọc Song ngữ</span>
                        </button>
                        <button
                          onClick={() => handleOpenExplorer(result.dual!)}
                          className="py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center justify-center gap-1.5 border border-slate-700 transition"
                        >
                          <FolderOpen className="w-3.5 h-3.5" />
                          <span>Mở thư mục</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex justify-between items-center">
                <span>Thư mục xuất: {result.output_dir}</span>
              </div>
            </div>
          ) : (
            !isTranslating && (
              <div className="flex-1 bg-slate-900/50 border border-slate-800/60 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-slate-800/40 border border-slate-700/40 flex items-center justify-center mb-4 text-slate-400">
                  <BookOpen className="w-8 h-8" />
                </div>
                <h3 className="font-semibold text-slate-300 text-base mb-1">Chưa có bản dịch nào</h3>
                <p className="text-xs text-slate-500 max-w-sm">
                  Hãy chọn tệp PDF ở bảng bên trái và bấm <strong className="text-slate-400">Bắt đầu Dịch</strong>. Hệ thống sẽ tự động giữ nguyên 100% công thức toán học và hình ảnh.
                </p>
              </div>
            )
          )}
        </section>
      </main>

      {/* OpenCode-Style Custom Provider Modal */}
      {showCustomModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 animate-scale-in max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 shrink-0">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-base text-slate-200">
                  {editingProviderId ? `Chỉnh sửa Provider: ${formDisplayName || formProviderId}` : "Custom provider"}
                </h3>
              </div>
              <button
                onClick={() => setShowCustomModal(false)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            {/* Description */}
            <p className="text-xs text-slate-400 shrink-0">
              Cấu hình nhà cung cấp tương thích chuẩn <strong>OpenAI Chat Completions API</strong> (OpenRouter, Groq, Together, vLLM, LMStudio, v.v.).
            </p>

            {/* Form Body (Scrollable) */}
            <div className="space-y-4 overflow-y-auto pr-1 flex-1">
              {formError && (
                <div className="p-2.5 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Provider ID */}
              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">Provider ID</label>
                <input
                  type="text"
                  value={formProviderId}
                  disabled={Boolean(editingProviderId)}
                  onChange={(e) => setFormProviderId(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))}
                  placeholder="myprovider"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono disabled:opacity-50"
                />
                <p className="text-[10px] text-slate-500 mt-1">Chữ cái viết thường, số, dấu gạch ngang (-) hoặc gạch dưới (_)</p>
              </div>

              {/* Display Name */}
              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">Display name</label>
                <input
                  type="text"
                  value={formDisplayName}
                  onChange={(e) => setFormDisplayName(e.target.value)}
                  placeholder="My AI Provider (vd: Vllao, OpenRouter, Groq Cloud...)"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Base URL */}
              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">Base URL</label>
                <input
                  type="text"
                  value={formBaseUrl}
                  onChange={(e) => setFormBaseUrl(e.target.value)}
                  placeholder="https://api.myprovider.com/v1"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>

              {/* API key */}
              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">API key</label>
                <input
                  type="password"
                  value={formApiKey}
                  onChange={(e) => setFormApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1">Tùy chọn. Để trống nếu dùng mạng cục bộ / proxy không cần khóa xác thực.</p>
              </div>

              {/* Models List */}
              <div className="space-y-2 pt-2 border-t border-slate-800/80">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="text-xs text-slate-200 font-bold block">Danh sách Models</label>
                    <p className="text-[10px] text-slate-500">Thêm bao nhiêu model tùy ý cho API này</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFormModels([...formModels, { id: "", name: "" }])}
                    className="px-2.5 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 text-xs font-semibold flex items-center gap-1 transition"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Thêm Model</span>
                  </button>
                </div>

                <div className="space-y-2 mt-2">
                  {formModels.map((m, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 rounded-xl bg-slate-950/60 border border-slate-800">
                      <div className="flex-1">
                        <label className="text-[10px] text-slate-500 block mb-0.5">Model ID</label>
                        <input
                          type="text"
                          placeholder="vd: gpt-4o, spd/deepseek-v6-flash"
                          value={m.id}
                          onChange={(e) => {
                            const updated = [...formModels];
                            updated[idx].id = e.target.value;
                            setFormModels(updated);
                          }}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 font-mono"
                        />
                      </div>
                      <div className="flex-1">
                        <label className="text-[10px] text-slate-500 block mb-0.5">Tên hiển thị</label>
                        <input
                          type="text"
                          placeholder="vd: DeepSeek V3 Flash"
                          value={m.name}
                          onChange={(e) => {
                            const updated = [...formModels];
                            updated[idx].name = e.target.value;
                            setFormModels(updated);
                          }}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                        />
                      </div>
                      {formModels.length > 1 && (
                        <div className="pt-3">
                          <button
                            type="button"
                            onClick={() => setFormModels(formModels.filter((_, i) => i !== idx))}
                            className="p-1.5 rounded-lg bg-rose-950/30 hover:bg-rose-900/50 text-rose-400 hover:text-rose-300 border border-rose-900/40 transition"
                            title="Xóa model này"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Actions Footer */}
            <div className="pt-3 border-t border-slate-800 flex items-center justify-between shrink-0">
              {editingProviderId ? (
                <button
                  type="button"
                  onClick={() => {
                    if (confirm(`Bạn có chắc chắn muốn xóa toàn bộ Provider "${formDisplayName || editingProviderId}" không?`)) {
                      handleDeleteCustomProvider(editingProviderId);
                    }
                  }}
                  className="py-2 px-3 rounded-xl bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 border border-rose-800/80 text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Xóa Provider này</span>
                </button>
              ) : (
                <div></div>
              )}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowCustomModal(false)}
                  className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={handleSaveCustomProvider}
                  className="py-2 px-5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-blue-500/20 transition"
                >
                  Lưu cấu hình
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Standard Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-base text-slate-200 flex items-center gap-2">
                <Settings className="w-4 h-4 text-blue-400" />
                <span>Cài đặt API Keys (Tùy chọn)</span>
              </h3>
              <button
                onClick={() => setShowSettings(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Nếu bạn chỉ dùng <strong>Google / Bing Translate</strong> (miễn phí), bạn không cần nhập bất kỳ key nào ở đây.
            </p>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">OpenAI API Key (sk-...)</label>
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-proj-..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">DeepSeek API Key (sk-...)</label>
                <input
                  type="password"
                  value={deepseekKey}
                  onChange={(e) => setDeepseekKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 block mb-1 font-medium">Google Gemini API Key</label>
                <input
                  type="password"
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  placeholder="AIzaSy..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="py-1.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleSaveSettings}
                className="py-1.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition"
              >
                Lưu cài đặt
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
