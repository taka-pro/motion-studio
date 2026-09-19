export const defaults={x:56,y:104,size:100,body:4,head:1.3,hair:10,chest:38,cycle:2,blink:true,bgMode:'image',bgZoom:100,bgX:0,bgY:0,blur:3,brightness:96,color:'#27384d',duration:8,fps:30,resolution:1080};
const I=()=>[1,0,0,0,1,0,0,0,1];
const T=(x,y)=>[1,0,0,0,1,0,x,y,1];
const S=(s)=>[s,0,0,0,s,0,0,0,1];
const R=(a)=>{a*=Math.PI/180;return [Math.cos(a),Math.sin(a),0,-Math.sin(a),Math.cos(a),0,0,0,1]};
const mul=(a,b)=>{const o=Array(9).fill(0);for(let c=0;c<3;c++)for(let r=0;r<3;r++)for(let k=0;k<3;k++)o[c*3+r]+=a[k*3+r]*b[c*3+k];return o};
const chain=(...a)=>a.reduce(mul,I());
const pivot=(p,a)=>chain(T(...p),R(a),T(-p[0],-p[1]));
export const imageFrom=(url)=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=()=>reject(new Error('画像を読み込めませんでした'));im.src=url;});
export class Renderer{
 constructor(){
  this.surface=document.createElement('canvas');
  const gl=this.gl=this.surface.getContext('webgl',{alpha:true,premultipliedAlpha:true,antialias:false,preserveDrawingBuffer:true});
  if(!gl)throw Error('WebGLを利用できません。ChromeまたはEdgeで開いてください。');
  this.surface.addEventListener('webglcontextlost',e=>{e.preventDefault();this.lost=true;});
  const vs=`attribute vec2 a_uv;uniform mat3 u_matrix;uniform vec4 u_box;uniform vec2 u_resolution;varying vec2 v_local;void main(){v_local=u_box.xy+a_uv*u_box.zw;vec3 p=u_matrix*vec3(v_local,1.0);gl_Position=vec4(p.x/u_resolution.x*2.0-1.0,1.0-p.y/u_resolution.y*2.0,0,1);}`;
  const fs=`precision highp float;uniform sampler2D u_texture;uniform vec4 u_box;uniform vec2 u_shift;varying vec2 v_local;void main(){float r=length((v_local-vec2(896.0,1340.0))/vec2(405.0,425.0));float w=r<1.0?(1.0+cos(3.14159265*r))*0.5:0.0;vec2 uv=(v_local-u_shift*w-u_box.xy)/u_box.zw;if(uv.x<0.0||uv.y<0.0||uv.x>1.0||uv.y>1.0)discard;gl_FragColor=texture2D(u_texture,uv);}`;
  const shader=(type,src)=>{const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s};
  const program=this.program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('描画プログラムを初期化できません');gl.useProgram(program);
  const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,1,0,0,1,0,1,1,0,1,1]),gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(program,'a_uv');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  this.u={};for(const n of ['matrix','box','resolution','shift','texture'])this.u[n]=gl.getUniformLocation(program,'u_'+n);
  gl.uniform1i(this.u.texture,0);gl.enable(gl.BLEND);gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
  this.bgCanvas=document.createElement('canvas');this.bgKey='';this.bgVersion=0;
 }
 async load(){
  const response=await fetch('/assets/parts.json');if(!response.ok)throw Error('パーツ一覧を読み込めません');this.manifest=await response.json();
  this.parts=await Promise.all(this.manifest.parts.map(async p=>{
   const im=await imageFrom(p.url),gl=this.gl,texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);return {...p,texture};
  }));
 }
 setBackground(im){this.bgImage=im;this.bgVersion++;}
 background(ctx,w,h,c){
  const key=JSON.stringify([w,h,c.bgMode,c.bgZoom,c.bgX,c.bgY,c.blur,c.brightness,c.color,this.bgVersion]);
  if(this.bgKey!==key){
   this.bgCanvas.width=w;this.bgCanvas.height=h;const b=this.bgCanvas.getContext('2d');b.fillStyle=c.color;b.fillRect(0,0,w,h);
   if(c.bgMode==='image'&&this.bgImage){
    const im=this.bgImage,margin=c.blur*h/720*3,scale=Math.max((w+2*margin)/im.width,(h+2*margin)/im.height)*c.bgZoom/100;
    const dw=im.width*scale,dh=im.height*scale;const x=(w-dw)/2+c.bgX/100*Math.max(0,(dw-w)/2-margin),y=(h-dh)/2+c.bgY/100*Math.max(0,(dh-h)/2-margin);
    b.filter=`blur(${c.blur*h/720}px) brightness(${c.brightness}%)`;b.drawImage(im,x,y,dw,dh);b.filter='none';
   }
   this.bgKey=key;
  }
  ctx.drawImage(this.bgCanvas,0,0);
 }
 render(canvas,time,c){
  if(this.lost)throw Error('GPUとの接続が切れました。設定を保存して画面を再読み込みしてください。');
  const w=canvas.width,h=canvas.height,ctx=canvas.getContext('2d',{alpha:false}),gl=this.gl;
  this.background(ctx,w,h,c);
  if(this.surface.width!==w||this.surface.height!==h){this.surface.width=w;this.surface.height=h;}
  gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.useProgram(this.program);gl.uniform2f(this.u.resolution,w,h);
  const p=time*2*Math.PI/c.cycle,body=chain(T(26*Math.sin(p-.2)*c.body/4,70+14*Math.cos(2*p)*c.body/4),pivot([896,2040],c.body*Math.sin(p))),head=pivot([898,746],-c.head*Math.sin(p-.25));
  const screen=chain(T(w*c.x/100,h*c.y/100),S(h*c.size/100/2240),T(-896,-2240));
  const b=time%4,eye=c.blink?((b>=2.2&&b<2.27)||(b>=2.37&&b<2.44)?'Half':b>=2.27&&b<2.37?'Closed':'Open'):'Open';
  for(const part of this.parts){
   if(part.name.includes('_Eye_')&&!part.name.endsWith(eye))continue;
   let angle=0;
   if(part.name==='12_Hair_ScreenLeft')angle=c.hair*(Math.sin(p-.75)+.16*Math.sin(2*p-1.1));
   if(part.name==='13_Hair_ScreenRight')angle=c.hair*(.9*Math.sin(p-.9)+.14*Math.sin(2*p-1.3));
   if(part.name==='11_Hair_Front')angle=c.hair*.065*Math.sin(p-.45);
   if(part.name==='02_Arm_ScreenLeft')angle=c.body*.4*Math.sin(p-.4);
   if(part.name==='03_Arm_ScreenRight')angle=c.body*.4*Math.sin(p-.45);
   const matrix=chain(screen,body,part.parent==='HEAD'?head:I(),pivot(part.pivot,angle));
   gl.uniformMatrix3fv(this.u.matrix,false,new Float32Array(matrix));const box=part.box;gl.uniform4f(this.u.box,box[0],box[1],box[2]-box[0],box[3]-box[1]);
   if(part.name==='01_Body_Base')gl.uniform2f(this.u.shift,c.chest/38*18*Math.sin(p-.5),c.chest*(Math.sin(2*p-.7)+.16*Math.sin(4*p-1.2)));else gl.uniform2f(this.u.shift,0,0);
   gl.bindTexture(gl.TEXTURE_2D,part.texture);gl.drawArrays(gl.TRIANGLES,0,6);
  }
  ctx.drawImage(this.surface,0,0);
 }
}
