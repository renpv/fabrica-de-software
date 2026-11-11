import { Navigate, Route, Routes } from "react-router";
import { TelaContas } from "../contas/TelaContas";
import { TelaPredefinicoes } from "../predefinicoes/TelaPredefinicoes";
import { TelaPlataformas } from "../plataformas/TelaPlataformas";
import { RotaProtegida } from "../sessao/RotaProtegida";
import { TelaLogin } from "../sessao/TelaLogin";
import { Layout } from "./Layout";

export function RotasApp() {
  return (
    <Routes>
      <Route path="/entrar" element={<TelaLogin />} />
      <Route element={<RotaProtegida />}>
        <Route element={<Layout />}>
          <Route path="/contas" element={<TelaContas />} />
          <Route path="/plataformas" element={<TelaPlataformas />} />
          <Route path="/predefinicoes" element={<TelaPredefinicoes />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/contas" replace />} />
    </Routes>
  );
}
