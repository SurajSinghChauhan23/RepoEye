import { ArrowLeft, Send, GripHorizontal, X, ZoomIn, ZoomOut, Star } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { apiService } from "../services/api";

export default function Workspace() {
  const navigate = useNavigate();
  const location = useLocation();
  const { repoUrl, repoId, fileTree } = location.state || {};

  const [parsingComplete, setParsingComplete] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [fileLoading, setFileLoading] = useState(false);
  const [expandedFolders, setExpandedFolders] = useState(new Set());

  const [messages, setMessages] = useState([
    { sender: "ai", text: "Repository analysis in progress. Please wait..." },
  ]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMode, setChatMode] = useState("explanation");
  const messagesEndRef = useRef(null);

  // Starred responses
  const [starredResponses, setStarredResponses] = useState([]);
  const [showStarred, setShowStarred] = useState(false);

  // Image modal state
  const [modalImage, setModalImage] = useState(null);
  const [imageZoom, setImageZoom] = useState(1);

  // Resizable chat
  const [chatHeight, setChatHeight] = useState(260);
  const [isResizing, setIsResizing] = useState(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(260);

  /* ---------------- MARKDOWN FORMATTING ---------------- */
  const formatMarkdown = (text) => {
    if (!text) return "";
    
    // Remove markdown headers (###, ##, #)
    let formatted = text.replace(/^#{1,6}\s+/gm, "");
    
    // Remove bold markers (**text**)
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, "$1");
    
    // Remove italic markers (*text* or _text_)
    formatted = formatted.replace(/[*_](.+?)[*_]/g, "$1");
    
    // Remove code block markers (```)
    formatted = formatted.replace(/```[\s\S]*?```/g, "");
    formatted = formatted.replace(/`(.+?)`/g, "$1");
    
    // Remove list markers (-, *, 1.)
    formatted = formatted.replace(/^[\s]*[-*]\s+/gm, "• ");
    formatted = formatted.replace(/^\d+\.\s+/gm, "");
    
    return formatted.trim();
  };

  /* ---------------- AUTO SCROLL TO BOTTOM ---------------- */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ---------------- STATUS POLLING (stops after completion) ---------------- */
  useEffect(() => {
    if (!repoId) return;

    let intervalId;

    const poll = async () => {
      try {
        const res = await apiService.getParsingStatus(repoId);
        if (res?.status === "completed") {
          setParsingComplete(true);
          setMessages([
            {
              sender: "ai",
              text:
                "Repository ingested successfully. Ask me anything about the codebase.",
            },
          ]);
          if (intervalId) {
            clearInterval(intervalId);
          }
        }
      } catch {}
    };

    poll();
    intervalId = setInterval(poll, 2000);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [repoId]);

  /* ---------------- RESIZABLE CHAT ---------------- */
  const handleMouseDown = (e) => {
    setIsResizing(true);
    startYRef.current = e.clientY;
    startHeightRef.current = chatHeight;
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const deltaY = startYRef.current - e.clientY;
      const newHeight = Math.min(Math.max(startHeightRef.current + deltaY, 200), 700);
      setChatHeight(newHeight);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  /* ---------------- FILE CONTENT LOADING ---------------- */
  async function loadFileContent(filePath) {
    setFileLoading(true);
    setSelectedFile(filePath);
    setFileContent("");

    try {
      const res = await apiService.getFileContent(repoId, filePath);
      setFileContent(res.content || "");
    } catch (err) {
      setFileContent("Error loading file content: " + err.message);
    } finally {
      setFileLoading(false);
    }
  }

  /* ---------------- CHAT ---------------- */
  async function sendMessage() {
    if (!input.trim() || !parsingComplete || chatLoading) return;

    const userMessage = input.trim();
    setInput("");

    setMessages((p) => [...p, { sender: "user", text: userMessage }]);

    setChatLoading(true);
    setMessages((p) => [
      ...p,
      {
        sender: "ai",
        text: "Processing your query... This may take some time.",
        loading: true,
      },
    ]);

    try {
      const res = await apiService.queryRepo(userMessage, chatMode);

      // Extract response data
      const responseData = res?.responses?.[chatMode];
      const responseText = responseData?.text || "I couldn't generate a response.";
      
      // Format markdown to plain text
      const formattedText = formatMarkdown(responseText);
      
      // Get image URL (construct full URL if relative path)
      let imageUrl = responseData?.image_url || null;
      if (imageUrl && !imageUrl.startsWith('http')) {
        imageUrl = `http://localhost:8000${imageUrl}`;
      }

      // Add timestamp to prevent caching
      if (imageUrl) {
        imageUrl = `${imageUrl}?t=${Date.now()}`;
      }

      setMessages((p) => {
        const withoutLoading = p.filter((m) => !m.loading);
        return [
          ...withoutLoading,
          {
            sender: "ai",
            text: formattedText,
            imageUrl: imageUrl,
            starred: false,
            id: Date.now(),
          },
        ];
      });
    } catch (err) {
      setMessages((p) => {
        const withoutLoading = p.filter((m) => !m.loading);
        return [
          ...withoutLoading,
          {
            sender: "ai",
            text: "Error occurred: " + (err.message || "Unknown error"),
          },
        ];
      });
    } finally {
      setChatLoading(false);
    }
  }

  /* ---------------- STAR RESPONSE ---------------- */
  const toggleStar = (messageId) => {
    setMessages((prevMessages) => {
      const updatedMessages = prevMessages.map((msg) => {
        if (msg.id === messageId && msg.sender === "ai") {
          return { ...msg, starred: !msg.starred };
        }
        return msg;
      });
      
      // Update starred responses based on the new messages state
      const newStarredResponses = updatedMessages.filter(
        (msg) => msg.sender === "ai" && msg.starred && msg.id
      );
      setStarredResponses(newStarredResponses);
      
      return updatedMessages;
    });
  };

  /* ---------------- IMAGE MODAL HANDLERS ---------------- */
  const openImageModal = (e, imageUrl) => {
    e.stopPropagation();
    e.preventDefault();
    console.log("Opening modal with image:", imageUrl);
    setModalImage(imageUrl);
    setImageZoom(1);
  };

  const closeImageModal = (e) => {
    e.stopPropagation();
    setModalImage(null);
    setImageZoom(1);
  };

  const zoomIn = (e) => {
    e.stopPropagation();
    setImageZoom((prev) => Math.min(prev + 0.25, 3));
  };

  const zoomOut = (e) => {
    e.stopPropagation();
    setImageZoom((prev) => Math.max(prev - 0.25, 0.5));
  };

  /* ---------------- UI ---------------- */
  return (
    <div
      style={{
        height: "100vh",
        background: "#020617",
        color: "#e5e7eb",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* HEADER */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "14px 24px",
          borderBottom: "1px solid #1e293b",
          flexShrink: 0,
        }}
      >
        <button
          onClick={() => navigate("/")}
          style={{
            background: "transparent",
            border: "none",
            color: "#cbd5f5",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <ArrowLeft size={16} /> Back
        </button>
        <span>{repoUrl?.split("/").slice(-2).join("/")}</span>
      </div>

      {!parsingComplete && (
        <div style={{ padding: "12px 24px", color: "#fbbf24", flexShrink: 0 }}>
          Parsing & indexing repository… Please wait
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "300px 1fr",
          flex: 1,
          overflow: "hidden",
        }}
      >
        {/* LEFT SIDEBAR */}
        <div
          style={{
            background: "#0f172a",
            borderRight: "1px solid #1e293b",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* TAB BUTTONS */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid #1e293b",
              flexShrink: 0,
            }}
          >
            <button
              onClick={() => setShowStarred(false)}
              style={{
                flex: 1,
                padding: "12px",
                background: !showStarred ? "#1e293b" : "transparent",
                border: "none",
                color: !showStarred ? "#60a5fa" : "#94a3b8",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              Files
            </button>
            <button
              onClick={() => setShowStarred(true)}
              style={{
                flex: 1,
                padding: "12px",
                background: showStarred ? "#1e293b" : "transparent",
                border: "none",
                color: showStarred ? "#60a5fa" : "#94a3b8",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
              }}
            >
              <Star size={14} fill={showStarred ? "#fbbf24" : "none"} stroke={showStarred ? "#fbbf24" : "#94a3b8"} />
              Starred ({starredResponses.length})
            </button>
          </div>

          {/* CONTENT */}
          <div style={{ flex: 1, overflowY: "auto", padding: 8 }}>
            {!showStarred ? (
              // FILE TREE
              fileTree ? (
                <TreeNode
                  node={fileTree}
                  expanded={expandedFolders}
                  setExpanded={setExpandedFolders}
                  onSelect={loadFileContent}
                />
              ) : (
                <div style={{ padding: 12, color: "#64748b", fontSize: 12 }}>
                  No files found
                </div>
              )
            ) : (
              // STARRED RESPONSES
              <div>
                {starredResponses.length === 0 ? (
                  <div style={{ padding: 12, color: "#64748b", fontSize: 12, textAlign: "center" }}>
                    No starred responses yet
                  </div>
                ) : (
                  starredResponses.map((msg, idx) => (
                    <div
                      key={msg.id}
                      style={{
                        background: "#1e293b",
                        padding: 12,
                        borderRadius: 6,
                        marginBottom: 8,
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                      onClick={() => {
                        // Scroll to this message in chat
                        const msgElement = document.getElementById(`msg-${msg.id}`);
                        if (msgElement) {
                          msgElement.scrollIntoView({ behavior: "smooth", block: "center" });
                        }
                      }}
                    >
                      <div style={{ color: "#94a3b8", marginBottom: 4, fontSize: 10 }}>
                        Response #{idx + 1}
                      </div>
                      <div style={{ color: "#e5e7eb", lineHeight: 1.4 }}>
                        {msg.text.substring(0, 100)}...
                      </div>
                      {msg.imageUrl && (
                        <div style={{ marginTop: 6, color: "#60a5fa", fontSize: 11 }}>
                          📊 Contains diagram
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT SIDE */}
        <div
          style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}
        >
          {/* FILE CONTENT AREA */}
          <div style={{ flex: 1, overflow: "auto", minHeight: 0 }}>
            {selectedFile ? (
              <div style={{ padding: 24, height: "100%" }}>
                <div
                  style={{
                    fontSize: 14,
                    color: "#94a3b8",
                    marginBottom: 12,
                    fontWeight: 500,
                  }}
                >
                  {selectedFile}
                </div>
                {fileLoading ? (
                  <div style={{ color: "#64748b", fontSize: 13 }}>
                    Loading file content...
                  </div>
                ) : (
                  <pre
                    style={{
                      background: "#0f172a",
                      padding: 16,
                      borderRadius: 8,
                      fontSize: 12,
                      lineHeight: 1.6,
                      overflow: "auto",
                      color: "#e5e7eb",
                      fontFamily: "monospace",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      margin: 0,
                    }}
                  >
                    {fileContent}
                  </pre>
                )}
              </div>
            ) : (
              <div style={{ padding: 24, color: "#64748b" }}>
                Select a file to view content
              </div>
            )}
          </div>

          {/* RESIZE HANDLE */}
          <div
            onMouseDown={handleMouseDown}
            style={{
              height: 8,
              background: "#1e293b",
              cursor: "ns-resize",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              userSelect: "none",
            }}
          >
            <GripHorizontal size={16} color="#64748b" />
          </div>

          {/* CHAT - RESIZABLE */}
          <div
            style={{
              borderTop: "1px solid #1e293b",
              padding: "12px 16px",
              height: chatHeight,
              background: "#0f172a",
              display: "flex",
              flexDirection: "column",
              flexShrink: 0,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 10,
              }}
            >
              <h3 style={{ fontSize: 13, margin: 0 }}>Chat</h3>

              {/* MODE SELECTOR */}
              <div
                style={{
                  display: "flex",
                  gap: 4,
                  background: "#020617",
                  borderRadius: 6,
                  padding: 2,
                }}
              >
                <button
                  onClick={() => setChatMode("explanation")}
                  disabled={chatLoading}
                  style={{
                    padding: "4px 12px",
                    fontSize: 11,
                    border: "none",
                    borderRadius: 4,
                    background:
                      chatMode === "explanation" ? "#2563eb" : "transparent",
                    color: chatMode === "explanation" ? "#fff" : "#94a3b8",
                    cursor: chatLoading ? "not-allowed" : "pointer",
                    fontWeight: 500,
                    opacity: chatLoading ? 0.5 : 1,
                  }}
                >
                  Explanation
                </button>
                <button
                  onClick={() => setChatMode("impact_analysis")}
                  disabled={chatLoading}
                  style={{
                    padding: "4px 12px",
                    fontSize: 11,
                    border: "none",
                    borderRadius: 4,
                    background:
                      chatMode === "impact_analysis"
                        ? "#2563eb"
                        : "transparent",
                    color: chatMode === "impact_analysis" ? "#fff" : "#94a3b8",
                    cursor: chatLoading ? "not-allowed" : "pointer",
                    fontWeight: 500,
                    opacity: chatLoading ? 0.5 : 1,
                  }}
                >
                  Impact Analysis
                </button>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: "auto", marginBottom: 10 }}>
              {messages.map((m, i) => (
                <div
                  key={i}
                  id={`msg-${m.id}`}
                  style={{
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      background: m.sender === "user" ? "#2563eb" : "#1e293b",
                      padding: "10px 14px",
                      borderRadius: 8,
                      fontSize: 13,
                      lineHeight: 1.5,
                      display: "inline-block",
                      maxWidth: "90%",
                      position: "relative",
                    }}
                  >
                    {m.loading && (
                      <div
                        style={{
                          width: 12,
                          height: 12,
                          border: "2px solid #334155",
                          borderTopColor: "#3b82f6",
                          borderRadius: "50%",
                          animation: "spin 1s linear infinite",
                          display: "inline-block",
                          marginRight: 8,
                          verticalAlign: "middle",
                        }}
                      />
                    )}
                    <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>

                    {/* RENDER IMAGE IF EXISTS */}
                    {m.imageUrl && (
                      <div style={{ marginTop: 12 }}>
                        <img
                          src={m.imageUrl}
                          alt="Generated diagram"
                          style={{
                            maxWidth: "100%",
                            height: "auto",
                            borderRadius: 6,
                            border: "1px solid #334155",
                            display: "block",
                            cursor: "pointer",
                          }}
                          onClick={(e) => openImageModal(e, m.imageUrl)}
                          onError={(e) => {
                            e.target.style.display = "none";
                            console.error("Failed to load image:", m.imageUrl);
                          }}
                        />
                      </div>
                    )}

                    {/* STAR BUTTON (only for AI responses with ID) */}
                    {m.sender === "ai" && m.id && (
                      <button
                        onClick={() => toggleStar(m.id)}
                        style={{
                          position: "absolute",
                          bottom: 8,
                          right: 8,
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                          padding: 4,
                        }}
                      >
                        <Star
                          size={16}
                          fill={m.starred ? "#fbbf24" : "none"}
                          stroke={m.starred ? "#fbbf24" : "#94a3b8"}
                        />
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                disabled={!parsingComplete || chatLoading}
                placeholder={
                  chatLoading
                    ? "Processing..."
                    : parsingComplete
                    ? "Ask about the codebase..."
                    : "Repository still processing..."
                }
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "#020617",
                  border: "1px solid #334155",
                  borderRadius: 6,
                  color: "#e5e7eb",
                }}
              />
              <button
                onClick={sendMessage}
                disabled={!parsingComplete || chatLoading}
                style={{
                  background: "#2563eb",
                  border: "none",
                  padding: "10px 12px",
                  borderRadius: 6,
                  cursor:
                    parsingComplete && !chatLoading ? "pointer" : "not-allowed",
                  opacity: parsingComplete && !chatLoading ? 1 : 0.5,
                }}
              >
                <Send size={14} color="white" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* IMAGE MODAL */}
      {modalImage && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.95)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 0,
          }}
          onClick={closeImageModal}
        >
          {/* CONTROLS */}
          <div
            style={{
              position: "fixed",
              top: 20,
              right: 20,
              display: "flex",
              gap: 8,
              zIndex: 10000,
            }}
          >
            <button
              onClick={zoomOut}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                color: "#e5e7eb",
                cursor: "pointer",
                padding: "8px 12px",
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              <ZoomOut size={16} /> Out
            </button>
            <button
              onClick={zoomIn}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                color: "#e5e7eb",
                cursor: "pointer",
                padding: "8px 12px",
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              <ZoomIn size={16} /> In
            </button>
            <button
              onClick={closeImageModal}
              style={{
                background: "#dc2626",
                border: "none",
                color: "#fff",
                cursor: "pointer",
                padding: "8px 12px",
                borderRadius: 6,
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              <X size={16} /> Close
            </button>
          </div>

          {/* IMAGE CONTAINER */}
          <div
            style={{
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              overflow: "auto",
              padding: 80,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={modalImage}
              alt="Full screen diagram"
              style={{
                transform: `scale(${imageZoom})`,
                transformOrigin: "center center",
                transition: "transform 0.2s ease",
                maxWidth: imageZoom > 1 ? "none" : "100%",
                maxHeight: imageZoom > 1 ? "none" : "100%",
                display: "block",
              }}
              onError={(e) => {
                console.error("Modal image failed to load:", modalImage);
                alert("Failed to load image. Please try again.");
                closeImageModal(e);
              }}
            />
          </div>
        </div>
      )}

      {/* SPINNER ANIMATION */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

/* ================= TREE NODE ================= */

function TreeNode({ node, expanded, setExpanded, onSelect, level = 0 }) {
  if (!node) return null;
  const isFile = node.type === "file";
  const isOpen = expanded.has(node.path);

  return (
    <div>
      <div
        onClick={() => {
          if (isFile) onSelect(node.path);
          else {
            const copy = new Set(expanded);
            copy.has(node.path) ? copy.delete(node.path) : copy.add(node.path);
            setExpanded(copy);
          }
        }}
        style={{
          paddingLeft: level * 16,
          cursor: "pointer",
          fontSize: 12,
          userSelect: "none",
          padding: "4px 8px",
          borderRadius: 4,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "#1e293b";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
        }}
      >
        {!isFile && (isOpen ? "▼" : "▶")} {isFile ? "📄" : "📁"} {node.name}
      </div>

      {!isFile &&
        isOpen &&
        node.children?.map((c, i) => (
          <TreeNode
            key={i}
            node={c}
            expanded={expanded}
            setExpanded={setExpanded}
            onSelect={onSelect}
            level={level + 1}
          />
        ))}
    </div>
  );
}
