import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { MotionGlobalConfig } from 'motion/react'
import { afterEach } from 'vitest'
import { queryClient } from '../lib/queryClient'

// Entry animations start at opacity 0; finishing them instantly keeps visibility assertions deterministic.
MotionGlobalConfig.skipAnimations = true

// The app-wide query cache would otherwise carry one test's responses into the next.
afterEach(()=>{cleanup();queryClient.clear()})
