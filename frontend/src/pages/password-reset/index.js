import { useContext } from "react"
import MetaTags from "react-meta-tags"
import { Redirect } from "react-router-dom"
import {
  Button,
  Container,
  Form,
  FormTitle,
  Input,
  Main,
} from "../../components"
import { AuthContext } from "../../contexts"
import { useFormWithValidation } from "../../utils"
import styles from "./styles.module.css"

const ResetPassword = ({ onPasswordReset }) => {
  const { values, handleChange, isValid, resetForm } = useFormWithValidation()
  const authContext = useContext(AuthContext)

  {
    authContext && <Redirect to="/recipes" />
  }

  return (
    <Main withBG asFlex>
      <Container className={styles.center}>
        <MetaTags>
          <title>Войти на сайт</title>
          <meta name="description" content="Фудграм - Сброс пароля" />
          <meta property="og:title" content="Сброс пароля" />
        </MetaTags>
        <Form
          className={styles.form}
          onSubmit={e => {
            e.preventDefault()
            onPasswordReset(values)
          }}
        >
          <FormTitle>Сброс пароля</FormTitle>

          <Input
            required
            name="email"
            placeholder="Email"
            onChange={handleChange}
          />
          <Button
            modifier="style_dark"
            disabled={!isValid}
            type="submit"
            className={styles.button}
          >
            Сбросить
          </Button>
        </Form>
      </Container>
    </Main>
  )
}

export default ResetPassword
