import { useMemo, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { motion } from "framer-motion"
import {
  ArrowRight,
  Bot,
  Cable,
  CheckCircle2,
  Code2,
  Copy,
  Cpu,
  Lightbulb,
  Play,
  RotateCcw,
  Send,
  Sparkles,
  TerminalSquare,
} from "lucide-react"
import { Button } from "@/components/ui/button"

type Difficulty = "Easy" | "Medium" | "Advanced"

interface BuildTemplate {
  title: string
  difficulty: Difficulty
  time: string
  board: string
  goal: string
  components: string[]
  promptSeed: string
  connections: Array<{
    from: string
    pin: string
    to: string
    wire: string
  }>
  code: string
}

const buildTemplates: BuildTemplate[] = [
  {
    title: "OLED Sensor Dashboard",
    difficulty: "Easy",
    time: "1 evening",
    board: "ESP32 DevKit V1",
    goal: "Cycle sensor readings on a small OLED screen.",
    components: ["ESP32 DevKit V1", "SSD1306 OLED Display", "DHT22 Temperature Humidity Sensor"],
    promptSeed: "Generate Arduino code for an ESP32 OLED sensor dashboard using SSD1306 over I2C and a DHT22 on GPIO 4. Show temperature and humidity, refresh every 2 seconds, and include comments for wiring.",
    connections: [
      { from: "ESP32 3V3", pin: "3V3", to: "OLED VCC + DHT22 VCC", wire: "red" },
      { from: "ESP32 GND", pin: "GND", to: "OLED GND + DHT22 GND", wire: "slate" },
      { from: "ESP32 GPIO 21", pin: "SDA", to: "OLED SDA", wire: "teal" },
      { from: "ESP32 GPIO 22", pin: "SCL", to: "OLED SCL", wire: "blue" },
      { from: "ESP32 GPIO 4", pin: "DATA", to: "DHT22 DATA", wire: "amber" },
    ],
    code: `#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

#define DHT_PIN 4
#define DHT_TYPE DHT22
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  dht.begin();
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
}

void loop() {
  float humidity = dht.readHumidity();
  float tempC = dht.readTemperature();

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("DIY HUB Sensor Dash");
  display.print("Temp: ");
  display.print(tempC);
  display.println(" C");
  display.print("Humidity: ");
  display.print(humidity);
  display.println(" %");
  display.display();

  delay(2000);
}`,
  },
  {
    title: "WiFi Temperature Logger",
    difficulty: "Easy",
    time: "1 evening",
    board: "ESP32 DevKit V1",
    goal: "Read a temperature/humidity sensor and publish readings over serial or WiFi.",
    components: ["ESP32 DevKit V1", "DHT22 Temperature Humidity Sensor", "10k resistor"],
    promptSeed: "Generate ESP32 Arduino code for a WiFi temperature logger using DHT22 on GPIO 4. Include placeholders for WiFi SSID/password, serial logs, and a simple JSON payload function.",
    connections: [
      { from: "ESP32 3V3", pin: "3V3", to: "DHT22 VCC", wire: "red" },
      { from: "ESP32 GND", pin: "GND", to: "DHT22 GND", wire: "slate" },
      { from: "ESP32 GPIO 4", pin: "DATA", to: "DHT22 DATA", wire: "amber" },
      { from: "10k resistor", pin: "PULLUP", to: "VCC to DATA", wire: "teal" },
    ],
    code: `#include <WiFi.h>
#include <DHT.h>

#define DHT_PIN 4
#define DHT_TYPE DHT22

const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";
DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(ssid, password);
}

void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  Serial.printf("{\\"temperature\\": %.2f, \\"humidity\\": %.2f}\\n", t, h);
  delay(5000);
}`,
  },
]

const fallbackTemplate = buildTemplates[0]

function WireLine({ connection, index }: { connection: BuildTemplate["connections"][number]; index: number }) {
  const colors: Record<string, string> = {
    red: "bg-rose-500",
    slate: "bg-slate-500",
    teal: "bg-teal-500",
    blue: "bg-sky-500",
    amber: "bg-amber-400",
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="grid gap-2 rounded-md border border-slate-900/10 bg-white p-3 text-sm dark:border-white/10 dark:bg-white/5 md:grid-cols-[1fr_auto_1fr]"
    >
      <div>
        <div className="text-xs font-bold uppercase text-slate-400">Controller</div>
        <div className="font-bold text-slate-900 dark:text-white">{connection.from}</div>
      </div>
      <div className="flex items-center gap-2 text-xs font-black text-slate-500 dark:text-slate-300">
        <span className={`h-1.5 w-12 rounded-full ${colors[connection.wire] ?? "bg-teal-500"}`} />
        <span>{connection.pin}</span>
        <ArrowRight className="h-4 w-4" />
      </div>
      <div>
        <div className="text-xs font-bold uppercase text-slate-400">Part</div>
        <div className="font-bold text-slate-900 dark:text-white">{connection.to}</div>
      </div>
    </motion.div>
  )
}

export default function BuildStudio() {
  const [params] = useSearchParams()
  const selectedTitle = params.get("idea")
  const selected = useMemo(
    () => buildTemplates.find((template) => template.title === selectedTitle) ?? fallbackTemplate,
    [selectedTitle],
  )
  const [prompt, setPrompt] = useState(selected.promptSeed)
  const [generated, setGenerated] = useState(false)

  function generateMockCode() {
    setGenerated(false)
    window.setTimeout(() => setGenerated(true), 350)
  }

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <section className="mb-5 overflow-hidden rounded-lg border border-slate-900/10 bg-slate-950 text-white shadow-[0_24px_80px_rgba(15,23,42,0.22)]">
        <div className="grid gap-5 p-5 sm:p-7 lg:grid-cols-[1fr_360px]">
          <div>
            <p className="inline-flex items-center gap-2 rounded-md bg-white/10 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-teal-100">
              <Bot className="h-3.5 w-3.5" />
              Build Studio
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-black leading-tight sm:text-5xl">
              Turn an idea into wiring and starter code.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              Preview flow only: choose a project, inspect pin connections, write the prompt, then generate a mock code draft.
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/10 p-4">
            <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
              <Lightbulb className="h-4 w-4 text-amber-300" />
              Selected idea
            </div>
            <div className="mt-4 text-2xl font-black">{selected.title}</div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold">
              <span className="rounded-md bg-teal-300/15 px-2 py-1 text-teal-100">{selected.board}</span>
              <span className="rounded-md bg-amber-300/15 px-2 py-1 text-amber-100">{selected.time}</span>
              <span className="rounded-md bg-white/10 px-2 py-1 text-slate-200">{selected.difficulty}</span>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="space-y-4">
          <div className="panel-surface rounded-lg p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-slate-950 dark:text-white">Pin Diagram</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">{selected.goal}</p>
              </div>
              <Cable className="h-6 w-6 text-teal-600" />
            </div>

            <div className="relative mb-4 overflow-hidden rounded-lg border border-slate-900/10 bg-slate-950 p-4 text-white dark:border-white/10">
              <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:22px_22px]" />
              <div className="relative grid gap-4 md:grid-cols-[1fr_0.65fr]">
                <div className="rounded-lg border border-teal-300/20 bg-white/8 p-4">
                  <div className="mb-3 flex items-center gap-2 text-sm font-black text-teal-100">
                    <Cpu className="h-4 w-4" />
                    {selected.board}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs font-bold">
                    {["3V3", "GND", "GPIO 4", "GPIO 21", "GPIO 22", "VIN", "EN", "GPIO 18"].map((pin) => (
                      <div key={pin} className="rounded-md border border-white/10 bg-slate-900 px-2 py-2 text-slate-200">
                        {pin}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="grid gap-2">
                  {selected.components.map((part) => (
                    <div key={part} className="rounded-md border border-white/10 bg-white/10 p-3 text-sm font-bold">
                      {part}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              {selected.connections.map((connection, index) => (
                <WireLine key={`${connection.from}-${connection.to}`} connection={connection} index={index} />
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div className="panel-surface rounded-lg p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-slate-950 dark:text-white">AI Code Prompt</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">This is the future AI handoff surface.</p>
              </div>
              <Sparkles className="h-6 w-6 text-amber-500" />
            </div>
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={8}
              className="w-full resize-none rounded-md border border-slate-900/10 bg-white p-3 text-sm leading-6 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-200 dark:border-white/10 dark:bg-slate-950 dark:text-white"
            />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-2 text-xs font-bold text-slate-500 dark:text-slate-400">
                <span className="rounded-md bg-slate-100 px-2 py-1 dark:bg-white/10">Arduino / ESP32</span>
                <span className="rounded-md bg-slate-100 px-2 py-1 dark:bg-white/10">Wiring-aware</span>
                <span className="rounded-md bg-slate-100 px-2 py-1 dark:bg-white/10">Mock AI output</span>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="gap-2" onClick={() => setPrompt(selected.promptSeed)}>
                  <RotateCcw className="h-4 w-4" />
                  Reset
                </Button>
                <Button size="sm" className="gap-2 bg-teal-700 hover:bg-teal-800" onClick={generateMockCode}>
                  <Send className="h-4 w-4" />
                  Generate code
                </Button>
              </div>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-slate-900/10 bg-slate-950 shadow-[0_18px_60px_rgba(15,23,42,0.16)] dark:border-white/10">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <div className="flex items-center gap-2 text-sm font-black text-white">
                <TerminalSquare className="h-4 w-4 text-teal-300" />
                Generated Code Draft
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" className="h-8 gap-2 text-slate-300 hover:bg-white/10 hover:text-white">
                  <Copy className="h-4 w-4" />
                  Copy
                </Button>
                <Button size="sm" variant="ghost" className="h-8 gap-2 text-slate-300 hover:bg-white/10 hover:text-white">
                  <Play className="h-4 w-4" />
                  Simulate
                </Button>
              </div>
            </div>
            <div className="max-h-[520px] overflow-auto p-4">
              {generated ? (
                <pre className="whitespace-pre-wrap text-sm leading-6 text-teal-50">
                  <code>{selected.code}</code>
                </pre>
              ) : (
                <div className="grid min-h-[300px] place-items-center rounded-md border border-dashed border-white/10 text-center">
                  <div>
                    <Code2 className="mx-auto mb-3 h-8 w-8 text-slate-500" />
                    <div className="text-sm font-bold text-slate-300">Code draft will appear here</div>
                    <div className="mt-1 text-xs text-slate-500">Press Generate code to preview the AI flow.</div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="panel-surface rounded-lg p-4">
            <div className="mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-teal-600" />
              <h2 className="text-base font-black text-slate-950 dark:text-white">Flow Preview</h2>
            </div>
            <div className="grid gap-2 text-sm text-slate-600 dark:text-slate-300 sm:grid-cols-3">
              <div className="rounded-md bg-white p-3 dark:bg-white/5">1. Confirm parts</div>
              <div className="rounded-md bg-white p-3 dark:bg-white/5">2. Review wiring</div>
              <div className="rounded-md bg-white p-3 dark:bg-white/5">3. Generate code</div>
            </div>
          </div>

          <Button asChild variant="outline" className="w-full">
            <Link to="/ideas">
              Back to Idea Lab
            </Link>
          </Button>
        </section>
      </div>
    </div>
  )
}
