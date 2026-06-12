import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"

export default function AddComponent() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.h1
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-3xl font-bold mb-2"
      >
        Add Component
      </motion.h1>
      <p className="text-slate-600 mb-6">
        Stage 1 placeholder. The form, image upload, and AI-suggest flow land
        in Stage 2 after NOFI approves Stage 1.
      </p>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="border-2 border-dashed border-slate-300 rounded-lg p-10 text-center bg-white"
      >
        <div className="text-slate-500">
          Add Component form will live here.
        </div>
        <div className="mt-4">
          <Button disabled>Add (disabled in Stage 1)</Button>
        </div>
      </motion.div>
    </div>
  )
}
