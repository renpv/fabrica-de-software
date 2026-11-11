import { Navigate, Route, Routes } from "react-router";
import { Pagina } from "../paginas/Pagina";
import { RotaProtegida } from "../sessao/RotaProtegida";
import { TelaLogin } from "../sessao/TelaLogin";
import { Layout } from "./Layout";

export function RotasApp() {
  return (
    <Routes>
      <Route path="/entrar" element={<TelaLogin />} />
      <Route element={<RotaProtegida />}>
        <Route element={<Layout />}>
          <Route path="/contas" element={<Pagina titulo="Contas de agente" />} />
          <Route path="/plataformas" element={<Pagina titulo="Plataformas e projetos" />} />
          <Route path="/predefinicoes" element={<Pagina titulo="Predefinições" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/contas" replace />} />
    </Routes>
  );
}
