import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorSummary, Field, Pagination, Status } from './UI'

describe('domain UI',()=>{
 it('does not rely on color for status',()=>{render(<Status value="validated"/>);expect(screen.getByText('Tekshirilgan')).toBeVisible()})
 it('focuses blocking error summaries and exposes them as alerts',()=>{render(<ErrorSummary error="Qayta tekshiring" title="Saqlanmadi"/>);expect(screen.getByRole('alert')).toHaveTextContent('Saqlanmadi');expect(screen.getByRole('alert')).toHaveFocus()})
 it('associates field hints and errors with invalid controls',()=>{render(<Field label="Kod" hint="Faqat kichik harf" error="Kod noto‘g‘ri"><input/></Field>);const input=screen.getByLabelText('Kod');expect(input).toHaveAttribute('aria-invalid','true');const ids=input.getAttribute('aria-describedby')?.split(' ')??[];expect(ids).toHaveLength(2);expect(ids.every(id=>document.getElementById(id))).toBe(true)})
 it('exposes deterministic pagination controls',()=>{const change=vi.fn();render(<Pagination offset={20} limit={20} total={55} onChange={change}/>);screen.getByRole('button',{name:'Keyingi'}).click();expect(change).toHaveBeenCalledWith(40)})
})
