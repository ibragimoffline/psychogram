import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { MotionGlobalConfig } from 'motion/react'
import { afterEach } from 'vitest'

// Entry animations start at opacity 0; finishing them instantly keeps visibility assertions deterministic.
MotionGlobalConfig.skipAnimations = true

afterEach(cleanup)
