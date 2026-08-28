import type { Metadata } from 'next';
import './globals.css';
import './integration.css';

export const metadata:Metadata={
  title:'PlanC — AI 旅行规划师',
  description:'用自然语言生成并持续调整你的多日旅行计划。',
  openGraph:{
    title:'PlanC — AI 旅行规划师',
    description:'每个旅行想法，都走得通。',
    type:'website',
    images:[{url:'/og.png',width:1733,height:908,alt:'PlanC AI 旅行规划师'}],
  },
  twitter:{
    card:'summary_large_image',
    title:'PlanC — AI 旅行规划师',
    description:'每个旅行想法，都走得通。',
    images:['/og.png'],
  },
};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="zh-CN"><body>{children}</body></html>}
