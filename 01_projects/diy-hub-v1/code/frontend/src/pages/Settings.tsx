import { motion } from "framer-motion"

export default function Settings() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold mb-2"
      >
        Settings
      </motion.h1>
      <p className="text-slate-600 mb-6">
        Stage 1 placeholder. Real settings (DB path, image dir, theme) land
        after the data layer is in place.
      </p>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="border rounded-lg p-10 text-center bg-white text-slate-500"
      >
        No settings exposed yet. Empty state — intentional.
      </motion.div>
    </div>
  )
}
