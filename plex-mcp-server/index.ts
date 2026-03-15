import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execPromise = promisify(exec);

class PlexManagerServer {
  private server: Server;
  private plexPath: string;

  constructor() {
    this.plexPath = process.env.PLEX_MEDIA_PATH || "/srv/media";
    this.server = new Server(
      {
        name: "plex-manager",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    
    // Error handling
    this.server.onerror = (error) => console.error("[MCP Error]", error);
    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: "list_library",
          description: "Lists all movie and show files in the Plex directory",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "audit_library",
          description: "Scans all media and identifies files that need transcoding",
          inputSchema: {
            type: "object",
            properties: {},
          },
        },
        {
          name: "transcode_video",
          description: "Optimizes a video file for Plex using Handbrake Flatpak (Intel QSV)",
          inputSchema: {
            type: "object",
            properties: {
              inputPath: {
                type: "string",
                description: "Full path to the source video file",
              },
            },
            required: ["inputPath"],
          },
        },
        {
          name: "swap_optimized_file",
          description: "Moves original file to Backup and replaces it with the Optimized version",
          inputSchema: {
            type: "object",
            properties: {
              originalPath: {
                type: "string",
                description: "Full path to the original movie file",
              },
            },
            required: ["originalPath"],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      switch (request.params.name) {
        case "list_library":
          return this.handleListLibrary();
        case "audit_library":
          return this.handleAuditLibrary();
        case "transcode_video":
          return this.handleTranscodeVideo(request.params.arguments);
        case "swap_optimized_file":
          return this.handleSwapOptimizedFile(request.params.arguments);
        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`
          );
      }
    });
  }

  private async handleListLibrary() {
    try {
      const { stdout } = await execPromise(`find ${this.plexPath} -maxdepth 3 -type f -regex ".*\\.\\(mkv\\|mp4\\)"`);
      return {
        content: [
          {
            type: "text",
            text: stdout || "No media files found.",
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Error listing library: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  private async handleAuditLibrary() {
    try {
      const { stdout: fileList } = await execPromise(`find ${this.plexPath} -maxdepth 3 -type f -regex ".*\\.\\(mkv\\|mp4\\)"`);
      const files = fileList.split("\n").filter(f => f.trim() !== "");
      
      let auditResults = "--- PLEX MEDIA AUDIT ---\n\n";
      
      for (const file of files) {
        try {
          const { stdout: probeOut } = await execPromise(`ffprobe -v error -show_entries stream=codec_name,channels -of default=noprint_wrappers=1:nokey=1 "${file}"`);
          const codecs = probeOut.toLowerCase();
          
          let issues = [];
          if (codecs.includes("av1")) issues.push("AV1 (Hardware Incompatible)");
          if (codecs.includes("vc1")) issues.push("VC-1 (Legacy/Heavy)");
          if (codecs.includes("truehd")) issues.push("TrueHD (Sync Drift Risk)");
          if (codecs.includes("dts")) issues.push("DTS-HD (Sync Drift Risk)");
          
          if (issues.length > 0) {
            auditResults += `⚠️ NEEDS UPDATE: ${path.basename(file)}\n   Reason: ${issues.join(", ")}\n   Path: ${file}\n\n`;
          }
        } catch (e) {
          auditResults += `❌ PROBE FAILED: ${path.basename(file)}\n\n`;
        }
      }
      
      if (!auditResults.includes("NEEDS UPDATE")) auditResults += "✅ All media is optimized!";
      
      return {
        content: [
          {
            type: "text",
            text: auditResults,
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Audit Error: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  private async handleTranscodeVideo(args: any) {
    if (!args?.inputPath) {
      throw new McpError(ErrorCode.InvalidParams, "inputPath is required");
    }
    const inputPath = args.inputPath as string;
    const ext = path.extname(inputPath);
    const outputPath = inputPath.replace(ext, `_Optimized${ext}`);
    const command = `flatpak run --command=HandBrakeCLI fr.handbrake.ghb -i "${inputPath}" -o "${outputPath}" --preset="H.265 QSV 1080p" -E ac3 -B 640`;

    try {
      exec(command); // Run in background
      return {
        content: [
          {
            type: "text",
            text: `Started transcoding in background: ${path.basename(inputPath)}`,
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Error starting transcode: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  private async handleSwapOptimizedFile(args: any) {
    if (!args?.originalPath) {
      throw new McpError(ErrorCode.InvalidParams, "originalPath is required");
    }
    const originalPath = args.originalPath as string;
    const ext = path.extname(originalPath);
    const optimizedPath = originalPath.replace(ext, `_Optimized${ext}`);
    const backupDir = path.join(path.dirname(originalPath), "Backup");
    const backupPath = path.join(backupDir, `${path.basename(originalPath, ext)}_Original_Raw${ext}`);

    try {
      await execPromise(`mkdir -p "${backupDir}"`);
      await execPromise(`mv "${originalPath}" "${backupPath}"`);
      await execPromise(`mv "${optimizedPath}" "${originalPath}"`);
      return {
        content: [
          {
            type: "text",
            text: `Successfully swapped ${path.basename(originalPath)}!`,
          },
        ],
      };
    } catch (error: any) {
      return {
        content: [
          {
            type: "text",
            text: `Error swapping file: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Plex Manager MCP server running on stdio");
  }
}

const server = new PlexManagerServer();
server.run().catch(console.error);
