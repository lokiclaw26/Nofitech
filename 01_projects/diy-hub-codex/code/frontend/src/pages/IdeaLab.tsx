import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { motion } from "framer-motion"
import { CheckCircle2, Lightbulb, Plus, Save, Sparkles, Wrench, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { componentText, fetchInventory, type ComponentItem } from "@/lib/inventory"

interface ProjectTemplate {
  title: string
  difficulty: "Easy" | "Medium" | "Advanced"
  time: string
  goal: string
  needs: string[]
  optional: string[]
  steps: string[]
}

interface SavedIdea {
  title: string
  savedAt: string
}

const templates: ProjectTemplate[] = [
  {
    title: "WiFi Temperature Logger",
    difficulty: "Easy",
    time: "1 evening",
    goal: "Read a temperature or humidity sensor and publish readings over WiFi.",
    needs: ["esp32|esp8266|wemos|d1 mini|nodemcu", "dht|bme280|bmp280|temperature|humidity", "resistor|breadboard|jumper"],
    optional: ["display|oled|lcd", "battery|lipo"],
    steps: ["Wire sensor power and data", "Flash a basic logger sketch", "Add web or MQTT output", "Place it in the room you want to monitor"],
  },
  {
    title: "Bench Power Monitor",
    difficulty: "Medium",
    time: "Weekend",
    goal: "Measure voltage and current on a small DC supply and show live readings.",
    needs: ["arduino|esp32|nano|uno", "ina219|current sensor|acs712|voltage sensor", "display|oled|lcd"],
    optional: ["rotary|encoder", "button", "case|enclosure"],
    steps: ["Calibrate voltage and current readings", "Build a compact display screen", "Add warning thresholds", "Mount near your bench supply"],
  },
  {
    title: "Smart Parts Drawer Beacon",
    difficulty: "Medium",
    time: "Weekend",
    goal: "Light up a drawer or box when you search for a component location.",
    needs: ["esp32|esp8266|wemos|nodemcu", "led|neopixel|ws2812", "resistor|jumper"],
    optional: ["button", "buzzer", "3d printed|case|enclosure"],
    steps: ["Assign LEDs to storage locations", "Serve a tiny local control page", "Trigger the LED for the searched drawer", "Add a timeout so it turns off automatically"],
  },
  {
    title: "Servo Test Jig",
    difficulty: "Easy",
    time: "1 evening",
    goal: "Quickly test hobby servos and sweep angles from a small controller.",
    needs: ["arduino|esp32|nano|uno", "servo|sg90|mg996", "potentiometer|rotary|button"],
    optional: ["display|oled|lcd", "buck|regulator"],
    steps: ["Wire servo power separately", "Read knob or buttons", "Sweep and center the servo", "Label safe voltage/current limits"],
  },
  {
    title: "OLED Sensor Dashboard",
    difficulty: "Easy",
    time: "1 evening",
    goal: "Make a compact display that cycles through sensor readings.",
    needs: ["arduino|esp32|esp8266|wemos", "display|oled|ssd1306|lcd", "sensor|temperature|pressure|light|motion"],
    optional: ["button", "encoder", "battery"],
    steps: ["Connect the display over I2C or SPI", "Read one or more sensors", "Create a simple page switcher", "Add a small enclosure or stand"],
  },
]

function matchesNeed(components: ComponentItem[], need: string) {
  const terms = need.split("|").map((term) => term.trim().toLowerCase())
  return components.find((component) => {
    const text = componentText(component)
    return terms.some((term) => text.includes(term))
  })
}

export default function IdeaLab() {
  const [components, setComponents] = useState<ComponentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<SavedIdea[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("diyhub-saved-ideas") || "[]")
    } catch {
      return []
    }
  })

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        setComponents(await fetchInventory())
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load inventory")
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  useEffect(() => {
    localStorage.setItem("diyhub-saved-ideas", JSON.stringify(saved))
  }, [saved])

  const ideas = useMemo(
    () =>
      templates
        .map((template) => {
          const owned = template.needs.map((need) => matchesNeed(components, need))
          const optionalOwned = template.optional.map((need) => matchesNeed(components, need)).filter(Boolean)
          const score = Math.round(((owned.filter(Boolean).length + optionalOwned.length * 0.35) / template.needs.length) * 100)
          return { template, owned, optionalOwned, score: Math.min(100, score) }
        })
        .sort((a, b) => b.score - a.score),
    [components],
  )

  function saveIdea(title: string) {
    setSaved((current) => {
      if (current.some((idea) => idea.title === title)) return current
      return [{ title, savedAt: new Date().toISOString() }, ...current]
    })
  }

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
          <p className="text-sm font-medium uppercase tracking-wide text-teal-700">Idea Lab</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-950">Project ideas from your parts</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Suggestions are matched against your inventory so you can start with what is already in your drawers.
          </p>
        </motion.div>
        <Button asChild>
          <Link to="/add">
            <Plus className="mr-2 h-4 w-4" />
            Add more parts
          </Link>
        </Button>
      </div>

      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <section className="space-y-4">
          {ideas.map(({ template, owned, optionalOwned, score }) => (
            <motion.article
              key={template.title}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-lg font-semibold text-slate-950">{template.title}</h2>
                    <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">{template.difficulty}</span>
                    <span className="rounded-md bg-teal-50 px-2 py-1 text-xs text-teal-700">{template.time}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{template.goal}</p>
                </div>
                <div className="shrink-0 text-left sm:text-right">
                  <div className="text-2xl font-semibold text-slate-950">{loading ? "..." : `${score}%`}</div>
                  <div className="text-xs text-slate-500">ready with inventory</div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-slate-900">Parts Check</h3>
                  <div className="space-y-2">
                    {template.needs.map((need, index) => {
                      const item = owned[index]
                      return (
                        <div key={need} className="flex items-start gap-2 text-sm">
                          {item ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-teal-600" /> : <XCircle className="mt-0.5 h-4 w-4 text-slate-300" />}
                          <div>
                            <div className="font-medium text-slate-800">{need.split("|").join(" / ")}</div>
                            <div className="text-xs text-slate-500">{item ? `${item.name}${item.location ? `, ${item.location}` : ""}` : "Not found in inventory"}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-slate-900">Build Path</h3>
                  <ol className="space-y-2 text-sm text-slate-600">
                    {template.steps.map((step) => (
                      <li key={step} className="flex gap-2">
                        <Wrench className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
                <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                  {optionalOwned.length > 0 ? (
                    <span className="rounded-md bg-indigo-50 px-2 py-1 text-indigo-700">{optionalOwned.length} optional upgrades owned</span>
                  ) : (
                    <span className="rounded-md bg-slate-100 px-2 py-1">No optional upgrades found yet</span>
                  )}
                </div>
                <Button size="sm" variant="outline" onClick={() => saveIdea(template.title)}>
                  <Save className="mr-2 h-4 w-4" />
                  Save idea
                </Button>
              </div>
            </motion.article>
          ))}
        </section>

        <aside className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-teal-700" />
              <h2 className="text-base font-semibold text-slate-950">How matching works</h2>
            </div>
            <p className="text-sm text-slate-600">
              Each idea searches names, models, categories, tags, specs, and interfaces. Better inventory notes make better ideas.
            </p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-amber-600" />
              <h2 className="text-base font-semibold text-slate-950">Saved Drafts</h2>
            </div>
            <div className="space-y-2">
              {saved.map((idea) => (
                <div key={idea.title} className="rounded-md bg-slate-50 p-3">
                  <div className="text-sm font-medium text-slate-900">{idea.title}</div>
                  <div className="mt-1 text-xs text-slate-500">Saved {new Date(idea.savedAt).toLocaleDateString()}</div>
                </div>
              ))}
              {saved.length === 0 && (
                <div className="rounded-md border border-dashed border-slate-300 p-5 text-center text-sm text-slate-500">
                  Saved project drafts will appear here.
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
