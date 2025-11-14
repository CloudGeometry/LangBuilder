import { Cookies } from "react-cookie";
import { LANGBUILDER_ACCESS_TOKEN } from "@/constants/constants";

export const customGetAccessToken = () => {
  const cookies = new Cookies();
  return cookies.get(LANGBUILDER_ACCESS_TOKEN);
};
