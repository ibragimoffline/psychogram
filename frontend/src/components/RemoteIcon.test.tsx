import { fireEvent, render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RemoteIcon } from './RemoteIcon'

describe('RemoteIcon',()=>{
  it('uses official Iconify Lucide API with accessible light-surface color',()=>{const {container}=render(<RemoteIcon name="shield"/>);const image=container.querySelector('img');expect(image).toHaveAttribute('src',expect.stringContaining('https://api.iconify.design/lucide/shield.svg?color=%2334443F'));expect(image).toHaveAttribute('referrerpolicy','no-referrer')})
  it('encodes an explicit dark-surface color',()=>{const {container}=render(<RemoteIcon name="users-round" color="#C8D4CF"/>);expect(container.querySelector('img')?.src).toContain('color=%23C8D4CF')})
  it('keeps a fixed fallback after remote failure',()=>{const {container}=render(<RemoteIcon name="shield" size={24}/>);fireEvent.error(container.querySelector('img')!);expect(container.querySelector('.icon-fallback')).toHaveTextContent('S');expect(container.firstChild).toHaveStyle({width:'24px',height:'24px'})})
})
