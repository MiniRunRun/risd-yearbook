/* Full-resolution 16-bit RGB composite. Original RAW samples remain 16-bit;
   artwork is decoded by the browser and may itself be 8-bit. */
'use strict';
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const smooth=(a,b,x)=>{if(b<=a)return x>=b?1:0;const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t)};
function blurBox(src,w,h,r){const tmp=new Float32Array(w*h),out=new Float32Array(w*h);r=Math.max(1,r|0);for(let y=0;y<h;y++){let n=0;for(let x=0;x<=r&&x<w;x++)n+=src[y*w+x];for(let x=0;x<w;x++){if(x){if(x-r-1>=0)n-=src[y*w+x-r-1];if(x+r<w)n+=src[y*w+x+r]}tmp[y*w+x]=n/(Math.min(w-1,x+r)-Math.max(0,x-r)+1)}}for(let x=0;x<w;x++){let n=0;for(let y=0;y<=r&&y<h;y++)n+=tmp[y*w+x];for(let y=0;y<h;y++){if(y){if(y-r-1>=0)n-=tmp[(y-r-1)*w+x];if(y+r<h)n+=tmp[(y+r)*w+x]}out[y*w+x]=n/(Math.min(h-1,y+r)-Math.max(0,y-r)+1)}}return out}
function bilinear(a,w,h,x,y){x=clamp(x,0,w-1);y=clamp(y,0,h-1);const ix=Math.floor(x),iy=Math.floor(y),jx=Math.min(ix+1,w-1),jy=Math.min(iy+1,h-1),dx=x-ix,dy=y-iy;return (a[iy*w+ix]*(1-dx)+a[iy*w+jx]*dx)*(1-dy)+(a[jy*w+ix]*(1-dx)+a[jy*w+jx]*dx)*dy}
const score=(r,g,b)=>(g-Math.max(r,b))/Math.max(35,g);
// Preserve artwork highlights while allowing fabric shadows to darken it.
function fabricLitColor(color,light){const x=clamp(color/255,0,1);if(light<=1)return x*Math.max(0,light)*255;const gain=.55*(1-Math.exp(-(light-1)/.55));return (x+(1-x)*(1-Math.exp(-gain*x)))*255;}
function composite(job){
 const {w,h,raw,regions,seg,globals}=job;if(!(raw instanceof Uint16Array)||raw.length!==w*h*3)throw Error('Expected full-resolution 16-bit RGB data.');
 // Sample illumination at modest resolution; the source and final pixel buffer remain full size.
 const lw=Math.max(1,Math.round(w*Math.min(1,1100/Math.max(w,h)))),lh=Math.max(1,Math.round(h*Math.min(1,1100/Math.max(w,h)))),green=new Float32Array(lw*lh);let sum=0,count=0;
 for(let y=0;y<lh;y++)for(let x=0;x<lw;x++){let sx=Math.min(w-1,Math.floor((x+.5)*w/lw)),sy=Math.min(h-1,Math.floor((y+.5)*h/lh)),k=(sy*w+sx)*3;green[y*lw+x]=raw[k+1]/257;}
 const blurred=blurBox(green,lw,lh,Math.max(2,Math.round(lw/160)));
 for(let y=0;y<lh;y+=2)for(let x=0;x<lw;x+=2){let k=(Math.min(h-1,Math.floor((y+.5)*h/lh))*w+Math.min(w-1,Math.floor((x+.5)*w/lw)))*3;if(score(raw[k]/257,raw[k+1]/257,raw[k+2]/257)>.15){sum+=blurred[y*lw+x];count++;}}
 const mean=count?sum/count:130,out=new Uint16Array(raw),threshold=globals.threshold/100,feather=Math.max(.001,globals.feather/100);
 for(let ri=0;ri<regions.length;ri++){
  const region=regions[ri];if(!region.art)continue;let mask=null;
  if(region.kind==='auto'&&seg){const m=new Float32Array(seg.w*seg.h);for(let i=0;i<m.length;i++)if(seg.labels[i]===region.segLabel)m[i]=seg.alpha[i]/255;mask=globals.feather>0?blurBox(m,seg.w,seg.h,Math.max(1,Math.round(globals.feather/30*2))):m;}
  const aw=region.art.w,ah=region.art.h,art=region.art.data,settings=region.settings,zoom=settings.zoom/100,warp=settings.warp*(w/1400),lighting=settings.lighting/100,texture=settings.texture/100;
  const N=Math.round(Math.sqrt(region.mesh.length));if(N*N!==region.mesh.length)throw Error('Invalid mesh.');const vertices=region.mesh.map((p,i)=>({x:p.x*w,y:p.y*h,u:(i%N)/(N-1),v:Math.floor(i/N)/(N-1)}));
  const xs=vertices.map(p=>p.x),ys=vertices.map(p=>p.y),mw=Math.max(1,Math.max(...xs)-Math.min(...xs)),mh=Math.max(1,Math.max(...ys)-Math.min(...ys));
  function tri(a,b,c){const den=(b.y-c.y)*(a.x-c.x)+(c.x-b.x)*(a.y-c.y);if(Math.abs(den)<1e-5)return;const x0=Math.max(0,Math.floor(Math.min(a.x,b.x,c.x))),x9=Math.min(w-1,Math.ceil(Math.max(a.x,b.x,c.x))),y0=Math.max(0,Math.floor(Math.min(a.y,b.y,c.y))),y9=Math.min(h-1,Math.ceil(Math.max(a.y,b.y,c.y)));
   for(let y=y0;y<=y9;y++)for(let x=x0;x<=x9;x++){const px=x+.5,py=y+.5,p1=((b.y-c.y)*(px-c.x)+(c.x-b.x)*(py-c.y))/den,p2=((c.y-a.y)*(px-c.x)+(a.x-c.x)*(py-c.y))/den,p3=1-p1-p2;if(p1<-.0001||p2<-.0001||p3<-.0001)continue;
    const idx=y*w+x,k=idx*3,r=raw[k]/257,g=raw[k+1]/257,bl=raw[k+2]/257,sc=score(r,g,bl);let opacity;
    if(mask){const spatial=bilinear(mask,seg.w,seg.h,(x+.5)*seg.w/w-.5,(y+.5)*seg.h/h-.5);if(spatial<.001)continue;const chroma=smooth(threshold-feather*.5,threshold+feather*.5,sc),dark=globals.recovery/100*(1-smooth(45,120,Math.max(r,g,bl)));opacity=spatial*Math.max(chroma,dark)}else{opacity=smooth(threshold-feather*.5,threshold+feather*.5,sc);if(globals.recovery>0&&g>=6&&g>Math.max(r,bl))opacity=Math.max(opacity,smooth(.015,.11,sc)*globals.recovery/100)}if(opacity<.002)continue;
    const lx=(x+.5)*lw/w-.5,ly=(y+.5)*lh/h-.5,shade=bilinear(blurred,lw,lh,lx,ly),dgx=(bilinear(blurred,lw,lh,lx+11*lw/w,ly)-bilinear(blurred,lw,lh,lx-11*lw/w,ly))/255,dgy=(bilinear(blurred,lw,lh,lx,ly+11*lh/h)-bilinear(blurred,lw,lh,lx,ly-11*lh/h))/255;
    let u=p1*a.u+p2*b.u+p3*c.u,v=p1*a.v+p2*b.v+p3*c.v;u+=(dgx*warp*2.4+(shade-mean)/Math.max(45,mean)*warp*.25)/mw;v+=dgy*warp*1.2/mh;u=(u-.5)/zoom+.5;v=(v-.5)/zoom+.5;
    const fx=clamp(u*(aw-1),0,aw-1),fy=clamp(v*(ah-1),0,ah-1),ax=Math.floor(fx),ay=Math.floor(fy),bx=Math.min(aw-1,ax+1),by=Math.min(ah-1,ay+1),dx=fx-ax,dy=fy-ay,aa=(ay*aw+ax)*4,ab=(ay*aw+bx)*4,ba=(by*aw+ax)*4,bb=(by*aw+bx)*4;
    function sample(ch){return art[aa+ch]*(1-dx)*(1-dy)+art[ab+ch]*dx*(1-dy)+art[ba+ch]*(1-dx)*dy+art[bb+ch]*dx*dy}
    const alpha=opacity*sample(3)/255;if(alpha<.002)continue;const lum=clamp(shade/Math.max(30,mean),.22,2.1),light=clamp(1+(Math.pow(lum,.9)-1)*lighting+((g-shade)/255)*texture*1.9,.18,2.15);
    for(let c=0;c<3;c++)out[k+c]=clamp(Math.round(raw[k+c]*(1-alpha)+fabricLitColor(sample(c),light)*257*alpha),0,65535);
   }
  }
  for(let y=0;y<N-1;y++)for(let x=0;x<N-1;x++){const a=vertices[y*N+x],b=vertices[y*N+x+1],c=vertices[(y+1)*N+x],d=vertices[(y+1)*N+x+1];tri(a,b,d);tri(a,d,c);}
  postMessage({progress:ri+1,total:regions.length});
 }
 return out;
}
onmessage=e=>{try{const data=composite(e.data);postMessage({done:true,data},[data.buffer]);}catch(err){postMessage({error:err.message||String(err)});}};
