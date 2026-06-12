import { motion } from "framer-motion"

export default function IdeaLab() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold mb-2"
      >
        Idea Lab
      </motion.h1>
      <p className="text-slate-600 mb-6">
        Stage 1 placeholder. Idea generation and the "AI suggests, you confirm"
        flow land in a later stage.
      </p>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="border rounded-lg p-10 text-center bg-white text-slate-500"
      >
        No ideas drafted yet. Empty state — intentional.
      </motion.div>
    </div>
  )
}
