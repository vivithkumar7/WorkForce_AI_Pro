import axios from 'axios';
const api=axios.create({baseURL:import.meta.env.VITE_API_URL||'http://127.0.0.1:8000'});
api.interceptors.request.use(config=>{const token=localStorage.getItem('wf_token'); if(token) config.headers.Authorization=`Bearer ${token}`; return config;});
export async function login(email,password){const body=new URLSearchParams({username:email,password}); const {data}=await api.post('/api/auth/login',body,{headers:{'Content-Type':'application/x-www-form-urlencoded'}}); localStorage.setItem('wf_token',data.access_token); return data;}
export default api;
