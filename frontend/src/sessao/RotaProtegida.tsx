import { Center, Loader } from "@mantine/core";
import { Navigate, Outlet } from "react-router";
import { useSessao } from "./useSessao";

export function RotaProtegida() {
  const { sessao, carregando } = useSessao();

  if (carregando) {
    return (
      <Center mih="100vh">
        <Loader aria-label="Carregando" />
      </Center>
    );
  }
  if (!sessao) return <Navigate to="/entrar" replace />;
  return <Outlet />;
}
