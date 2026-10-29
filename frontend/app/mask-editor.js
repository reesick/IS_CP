export class MaskEditor {
  constructor(canvas, onChange) {
    this.canvas = canvas; this.context = canvas.getContext('2d'); this.onChange = onChange;
    this.image = null; this.rect = null; this.mode = 'selected'; this.bounds = {x:0,y:0,width:512,height:512}; this.enabled = true;
    canvas.addEventListener('pointerdown', event => {
      if (!this.image || !this.enabled) return;
      event.preventDefault(); canvas.setPointerCapture(event.pointerId); this.start = this.point(event); this.rect = {...this.start,width:0,height:0}; this.draw();
    });
    canvas.addEventListener('pointermove', event => {
      if (!this.start) return;
      const point = this.point(event);
      this.rect = {x:Math.min(point.x,this.start.x),y:Math.min(point.y,this.start.y),width:Math.abs(point.x-this.start.x),height:Math.abs(point.y-this.start.y)};
      this.draw(); this.onChange(this.rect);
    });
    const finish = () => { if (this.start) { this.start = null; this.draw(); this.onChange(this.rect); } };
    canvas.addEventListener('pointerup', finish); canvas.addEventListener('pointercancel', finish);
  }
  point(event) {
    const box = this.canvas.getBoundingClientRect();
    return {x:Math.round(Math.max(this.bounds.x,Math.min(this.bounds.x+this.bounds.width,(event.clientX-box.left)*512/box.width))),y:Math.round(Math.max(this.bounds.y,Math.min(this.bounds.y+this.bounds.height,(event.clientY-box.top)*512/box.height)))};
  }
  async load(url, geometry = {}) {
    this.image = await new Promise((resolve,reject) => { const img = new Image(); img.onload=()=>resolve(img); img.onerror=()=>reject(new Error('The image preview could not be loaded.')); img.src=url; });
    const padding=geometry.padding || [0,0,0,0];
    this.bounds={x:padding[0],y:padding[1],width:geometry.scaled_width || 512-padding[0]-padding[2],height:geometry.scaled_height || 512-padding[1]-padding[3]};
    this.rect=null; this.draw(); this.onChange(null);
  }
  setRect(rect) {
    const x=Math.min(this.bounds.x+this.bounds.width,Math.max(this.bounds.x,Number(rect.x)||0));
    const y=Math.min(this.bounds.y+this.bounds.height,Math.max(this.bounds.y,Number(rect.y)||0));
    this.rect={x,y,width:Math.min(this.bounds.x+this.bounds.width-x,Math.max(0,Number(rect.width)||0)),height:Math.min(this.bounds.y+this.bounds.height-y,Math.max(0,Number(rect.height)||0))}; this.draw(); this.onChange(this.rect);
  }
  clear(){this.rect=null;this.draw();this.onChange(null);}
  setMode(mode){this.mode=mode;this.draw();this.onChange(this.rect);}
  draw() {
    const ctx=this.context; ctx.clearRect(0,0,512,512); if (!this.image) return; ctx.drawImage(this.image,0,0,512,512);
    const r=this.rect; if (!r || !r.width || !r.height) return;
    ctx.fillStyle='rgba(37,99,235,0.27)';
    if(this.mode==='background'){
      const b=this.bounds;ctx.beginPath();ctx.rect(b.x,b.y,b.width,b.height);ctx.rect(r.x,r.y,r.width,r.height);ctx.fill('evenodd');
    }else ctx.fillRect(r.x,r.y,r.width,r.height);
    ctx.strokeStyle='#2563eb';ctx.lineWidth=2;ctx.setLineDash([6,4]);ctx.strokeRect(r.x+.5,r.y+.5,r.width,r.height);ctx.setLineDash([]);
    for(const [x,y] of [[r.x,r.y],[r.x+r.width,r.y],[r.x,r.y+r.height],[r.x+r.width,r.y+r.height]]){ctx.fillStyle='#fff';ctx.fillRect(x-3,y-3,6,6);ctx.strokeRect(x-3,y-3,6,6);}
  }
  editableFraction(){if(!this.rect)return 0;const fraction=this.rect.width*this.rect.height/(this.bounds.width*this.bounds.height);return this.mode==='background'?1-fraction:fraction;}
  async blob() {
    if(!this.rect || !this.rect.width || !this.rect.height)throw new Error('Select an edit region first.');
    const fraction=this.editableFraction(); if(fraction<.05 || fraction>.95)throw new Error('Keep at least 5% editable and 5% retained. Adjust the region selection.');
    const canvas=document.createElement('canvas');canvas.width=canvas.height=512;const ctx=canvas.getContext('2d');ctx.fillStyle='#000';ctx.fillRect(0,0,512,512);
    const r=this.rect,b=this.bounds;ctx.fillStyle='#fff';if(this.mode==='background'){ctx.fillRect(b.x,b.y,b.width,b.height);ctx.fillStyle='#000';}ctx.fillRect(r.x,r.y,r.width,r.height);
    return await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
  }
}
