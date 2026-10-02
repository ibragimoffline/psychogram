import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { ErrorBoundary } from './ErrorBoundary'

function Broken():ReactNode{throw new Error('PII: secret value')}
describe('ErrorBoundary',()=>{it('shows only safe recovery copy',()=>{vi.spyOn(console,'error').mockImplementation(()=>undefined);render(<ErrorBoundary><Broken/></ErrorBoundary>);expect(screen.getByRole('alert')).toHaveTextContent('Interfeysni ochib bo‘lmadi');expect(screen.queryByText(/secret value/)).not.toBeInTheDocument()})})
