import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { useReducedMotion } from 'motion/react'
import { Button, ConfirmAction, Drawer, Page } from './UI'

vi.mock('motion/react',async(importOriginal)=>{const actual=await importOriginal<typeof import('motion/react')>();return{...actual,useReducedMotion:vi.fn()}})

function Harness(){const [open,setOpen]=useState(false);return <><button onClick={()=>setOpen(true)}>Panelni ochish</button><Drawer open={open} title="Sinov paneli" onClose={()=>setOpen(false)}><input aria-label="Birinchi maydon"/><Button>Oxirgi amal</Button></Drawer></>}
function ConfirmHarness(){const [open,setOpen]=useState(false);return <><button onClick={()=>setOpen(true)}>PIIni o‘chirish</button><ConfirmAction open={open} title="PII yozuvini o‘chirish" description="Bu amal qaytarilmaydi." confirmLabel="Ha, o‘chirish" onConfirm={()=>setOpen(false)} onCancel={()=>setOpen(false)}/></>}

describe('Drawer accessibility',()=>{
 it('moves focus, traps Tab, closes with Escape and restores opener',async()=>{vi.mocked(useReducedMotion).mockReturnValue(false);render(<Harness/>);const opener=screen.getByRole('button',{name:'Panelni ochish'});opener.focus();fireEvent.click(opener);const close=await screen.findByRole('button',{name:'Yopish'});await waitFor(()=>expect(close).toHaveFocus());fireEvent.keyDown(screen.getByRole('dialog'),{key:'Tab',shiftKey:true});expect(screen.getByRole('button',{name:'Oxirgi amal'})).toHaveFocus();fireEvent.keyDown(screen.getByRole('dialog'),{key:'Escape'});await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());expect(opener).toHaveFocus()})
 it('removes route translation when reduced motion is requested',()=>{vi.mocked(useReducedMotion).mockReturnValue(true);const {container}=render(<Page title="Sokin sahifa"><p>Kontent</p></Page>);expect(container.querySelector('.page')?.getAttribute('style')??'').not.toContain('translateY')})
 it('gives destructive confirmation cancel-first focus, trap, Escape and restore',async()=>{vi.mocked(useReducedMotion).mockReturnValue(false);render(<ConfirmHarness/>);const opener=screen.getByRole('button',{name:'PIIni o‘chirish'});opener.focus();fireEvent.click(opener);const dialog=await screen.findByRole('alertdialog');const cancel=screen.getByRole('button',{name:'Bekor qilish'});await waitFor(()=>expect(cancel).toHaveFocus());fireEvent.keyDown(dialog,{key:'Tab',shiftKey:true});expect(screen.getByRole('button',{name:'Ha, o‘chirish'})).toHaveFocus();fireEvent.keyDown(dialog,{key:'Escape'});await waitFor(()=>expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());expect(opener).toHaveFocus()})
})
