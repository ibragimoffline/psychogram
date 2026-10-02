import { describe, expect, it } from 'vitest'
import { readCsvFile } from './ResultImportPages'

function file(bytes:Uint8Array,name='answers.csv'){
 const value=new File([bytes],name,{type:'text/csv'});Object.defineProperty(value,'arrayBuffer',{value:()=>Promise.resolve(bytes.buffer)});return value
}
describe('CSV precheck',()=>{
 it('rejects oversized files before decoding',async()=>{await expect(readCsvFile(file(new Uint8Array(4)),3)).rejects.toThrow(/limitdan oshdi/)})
 it('rejects malformed UTF-8 fatally',async()=>{await expect(readCsvFile(file(new Uint8Array([0xc3,0x28])),100)).rejects.toThrow(/UTF-8 formatida emas/)})
 it('returns only safe metadata and decoded text for valid CSV',async()=>{const bytes=new TextEncoder().encode('external_code,item\nP-1,2');await expect(readCsvFile(file(bytes),100)).resolves.toMatchObject({name:'answers.csv',lines:2,text:'external_code,item\nP-1,2'})})
})
