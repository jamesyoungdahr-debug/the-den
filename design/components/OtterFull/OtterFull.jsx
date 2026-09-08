import { OtterMark } from '../OtterMark/OtterMark.jsx';

const U={w:220,h:330};

/** The full-body otter: same primitives as OtterMark, one head, no new vocabulary. */
export function OtterFull({size=220,pose='sitting',expression='happy',style,...rest}){
  const scale=size/U.w;
  const sitting=pose==='sitting';
  const torso={top:sitting?126:120,h:sitting?150:172,w:sitting?116:100,left:sitting?52:60};
  return (
    <div style={{position:'relative',width:size,height:size*U.h/U.w,flex:'none',...style}} {...rest}>
      <div style={{position:'absolute',left:0,top:0,width:U.w,height:U.h,transform:'scale('+scale+')',transformOrigin:'top left'}}>
        {/* tail — one rounded rect, curved by rotation */}
        <div style={{position:'absolute',left:sitting?150:142,top:sitting?214:236,width:96,height:30,borderRadius:15,background:'var(--holt-current-deep)',transform:'rotate('+(sitting?-16:6)+'deg)',transformOrigin:'left center'}} />
        {/* torso */}
        <div style={{position:'absolute',left:torso.left,top:torso.top,width:torso.w,height:torso.h,borderRadius:'46% 46% 40% 40%/38% 38% 60% 60%',background:'var(--holt-current)'}} />
        {/* belly patch */}
        <div style={{position:'absolute',left:torso.left+24,top:torso.top+34,width:torso.w-48,height:torso.h-56,borderRadius:'50%',background:'var(--holt-lilac)'}} />
        {/* arms */}
        <div style={{position:'absolute',left:torso.left-16,top:torso.top+26,width:32,height:74,borderRadius:16,background:'var(--holt-current)',transform:'rotate(11deg)'}} />
        <div style={{position:'absolute',left:torso.left+torso.w-16,top:torso.top+26,width:32,height:74,borderRadius:16,background:'var(--holt-current)',transform:'rotate(-11deg)'}} />
        {/* feet */}
        <div style={{position:'absolute',left:torso.left+(sitting?4:8),top:torso.top+torso.h-14,width:46,height:26,borderRadius:'50%',background:'var(--holt-lilac)'}} />
        <div style={{position:'absolute',left:torso.left+torso.w-(sitting?50:54),top:torso.top+torso.h-14,width:46,height:26,borderRadius:'50%',background:'var(--holt-lilac)'}} />
        {/* head — unchanged OtterMark */}
        <OtterMark size={152} expression={expression} style={{position:'absolute',left:34,top:0}} />
      </div>
    </div>
  );
}
